#-*- coding: utf-8 -*-
from flask import Blueprint,request,render_template,g,Flask
from Modules import db_op,check,produce,loging,db_idc
from sqlalchemy import and_,distinct
import json
import redis
import datetime
from flask_sqlalchemy import SQLAlchemy
from pyecharts import Bar,Tree
app = Flask(__name__)
app.config.from_pyfile('../conf/sql.conf')
DB = SQLAlchemy(app)
app.config.from_pyfile('../conf/redis.conf')
logging = loging.Error()
redis_host = app.config.get('REDIS_HOST')
redis_port = app.config.get('REDIS_PORT')
redis_password = app.config.get('REDIS_PASSWORD')
RC = redis.StrictRedis(host=redis_host, port=redis_port,decode_responses=True)
redis_data = app.config.get('REDIS_DATA')
RC_CLUSTER = redis.StrictRedis(host=redis_data, port=redis_port,decode_responses=True)
page_app_service = Blueprint('app_service', __name__)
@page_app_service.route('/crontab')
def crontab():
    try:
        VALS = []
        lable = "线上crontab运行列表"
        tables = ('执行计划', '执行动作', 'IP', 'SSH端口', '主机名')
        db_crontab = db_idc.crontabs
        db_servers = db_idc.idc_servers
        servers = db_servers.query.with_entities(db_servers.id,db_servers.ip,db_servers.ssh_port,db_servers.hostname).filter(db_servers.hostname != '').all()
        servers = {info[0]:info[1:] for info in servers}
        vals  = db_crontab.query.with_entities(db_crontab.cron,db_crontab.action,db_crontab.server_id).all()
        vals = [list(val) for val in vals]
        for val in vals:
            VAL = []
            server_id = val.pop(-1)
            if server_id in servers:
                VAL.extend(val)
                VAL.extend(servers[server_id])
                VALS.append(VAL)
    except Exception as e:
        logging.error(e)
    return render_template('crontab.html',vals = VALS,tables = tables,lable=lable)

@page_app_service.route('/run_jar')
@page_app_service.route('/run_jar/<project>')
def run_jar(project=None):
    try:
        VALS = []
        lable = "线上JAR包运行列表"
        tables = ('进程','任务','所属业务','IP','SSH端口','主机名')
        db_project_other = db_op.project_other
        db_servers = db_idc.idc_servers
        db_business = db_op.business
        business = db_business.query.with_entities(db_business.id,db_business.business).all()
        business = {info[0]:info[1] for info in business}
        servers = db_servers.query.with_entities(db_servers.id,db_servers.ip,db_servers.ssh_port,db_servers.hostname).filter(db_servers.hostname != '').all()
        servers = {info[0]:info[1:] for info in servers}
        if project:
            vals  = db_project_other.query.with_entities(db_project_other.lable,
                                                         db_project_other.project,db_project_other.server_id,db_project_other.business_id).\
                filter(and_(db_project_other.lable=='java',db_project_other.project==project)).all()
        else:
            vals = db_project_other.query.with_entities(db_project_other.lable, db_project_other.project,
                                                        db_project_other.server_id,
                                                        db_project_other.business_id).filter(
                db_project_other.lable == 'java').all()
        vals = [list(val) for val in vals]
        for val in vals:
            VAL = []
            server_id = val.pop(2)
            business_id = val.pop(2)
            if server_id in servers:
                VAL.extend(val)
                if business_id == 0 or business_id not in business:
                    VAL.append('未知')
                else:
                    VAL.append(business[business_id])
                VAL.extend(servers[server_id])
                VALS.append(VAL)
    except Exception as e:
        logging.error(e)
    return render_template('run_jar.html',vals = VALS,tables = tables,lable=lable)

@page_app_service.route('/hosts')
@page_app_service.route('/hosts/<hostname>')
def hosts(hostname=None):
    try:
        VALS = []
        lable = " "
        tables = ('host', 'name', '主机', 'SSH端口', '主机名')
        db_hosts = db_idc.hosts
        db_servers = db_idc.idc_servers
        hostnames = db_servers.query.with_entities(db_servers.id,db_servers.hostname).all()
        exist_ids = db_hosts.query.with_entities(distinct(db_hosts.server_id)).all()
        exist_ids = [ id[0] for id in exist_ids]
        host_list = [{"id": str(id), "text": str(info)} for id,info in hostnames if id in exist_ids]
        if not hostname:
            hostname = host_list[0]['text']
        lable = "线上服务器({0})hosts列表".format(hostname)
        servers = db_servers.query.with_entities(db_servers.id,db_servers.ip,db_servers.ssh_port,db_servers.hostname).filter(db_servers.hostname == hostname).all()
        servers_info = servers[0][1:]
        server_id = servers[0][0]
        vals  = db_hosts.query.with_entities(db_hosts.host,db_hosts.hostname).filter(db_hosts.server_id==server_id).all()
        vals = [list(val) for val in vals]
        for val in vals:
            VAL = []
            VAL.extend(val)
            VAL.extend(servers_info)
            VALS.append(VAL)
    except Exception as e:
        logging.error(e)
    return render_template('hosts.html',vals = VALS,tables = tables,lable=lable,host_list=json.dumps(host_list))

@page_app_service.route('/redis_info')
def redis_info():
    try:
        lable = "线上REDIS信息汇总"
        tables = ('host', 'app_port', 'masterauth', 'requirepass', 'role(主)','role(从)','role(集群)','master_host','master_port')
        db_redis_info = db_idc.redis_info
        VALS = db_redis_info.query.with_entities(db_redis_info.server_id,db_redis_info.port,db_redis_info.masterauth,db_redis_info.requirepass,db_redis_info.master,db_redis_info.slave,
                                                  db_redis_info.cluster,db_redis_info.Master_Host,db_redis_info.Master_Port).all()
        VALS = [list(val) for val in VALS]
        for val in VALS:
            hostname = RC_CLUSTER.hget('op_server_hostnames',val[0])
            if hostname:
                val[0] = hostname
            hostname = RC_CLUSTER.hget('op_server_hostnames', val[-2])
            if hostname:
                val[-2] = hostname
    except Exception as e:
        logging.error(e)
    return render_template('redis_info.html',vals = VALS,tables = tables,lable=lable)

@page_app_service.route('/redis_status/<hostname>/<app_port>')
@page_app_service.route('/redis_master/<redis_master>')
def redis_status(hostname=None,app_port=None,redis_master=None):
    try:
        db_redis = db_idc.redis_info
        db_server = db_idc.idc_servers
        BARS = []
        DATA = []
        tree = None
        if hostname and app_port:
            try:
                for info in ('used_memory', 'hit_rate','clients', 'ops'):
                    attrs = []
                    vals = []
                    yf = ''
                    for i in range(7):
                        update_date = datetime.datetime.now() - datetime.timedelta(days=i)
                        update_date = update_date.strftime('%Y-%m-%d')
                        Key = 'op_redis_status_%s_%s_%s' % (hostname, app_port, update_date)
                        if RC_CLUSTER.exists(Key):
                            infos = RC_CLUSTER.hgetall(Key)
                            attrs.append(update_date)
                            val = infos[info]
                            if 'G' in infos[info]:
                                yf = 'G'
                                val = infos[info].replace('G', '')
                            if 'M' in infos[info]:
                                yf = 'M'
                                val = infos[info].replace('M', '')
                            vals.append(val)
                    bar = Bar(info, title_pos='center', width='100%', height='250px')
                    if info == 'used_memory':
                        bar.add("", attrs, vals, mark_point=["max", "min"], is_yaxislabel_align=True,
                            is_toolbox_show=False, xaxis_interval=0, legend_pos='100%',yaxis_formatter=yf,
                                is_random=True,xaxis_name_size=12,legend_text_size=12)
                    elif info == 'hit_rate':
                        bar.add("", attrs, vals, mark_point=["max", "min"], is_yaxislabel_align=True,
                            is_toolbox_show=False, xaxis_interval=0, legend_pos='100%',yaxis_formatter='%',
                            is_random=True,xaxis_name_size=12,legend_text_size=12)
                    else:
                        bar.add("", attrs, vals, mark_point=["max", "min"], is_yaxislabel_align=True,
                                is_toolbox_show=False, xaxis_interval=0, legend_pos='100%',
                                xaxis_name_size=12,legend_text_size=12)
                    BARS.append(bar)
            except Exception as e:
                logging.error(e)
        if redis_master:
            try:
                KEY = 'op_redis_master_lists'
                redis_master = redis_master.split(':')
                server_id = db_server.query.with_entities(db_server.id).filter(db_server.hostname==redis_master[0]).all()
                if server_id:
                    redis_master[0]=server_id[0][0]
                RC.lpush(KEY, redis_master)
                while True:
                    if RC.llen(KEY) > 0:
                        id, port = eval(RC.lpop(KEY))
                        vals = db_redis.query.with_entities(db_redis.server_id,db_redis.port).filter(and_(db_redis.Master_Host==id,db_redis.Master_Port==port)).all()
                        if vals:
                            key = 'op_redis_nexus_%s:%s' % (id, port)
                            RC.set(key, str(vals))
                            for val in vals:
                                RC.lpush(KEY, val)
                    else:
                        break
                id, port = redis_master
                hostname = RC_CLUSTER.hget('op_server_hostnames', id)
                if hostname:
                    name = hostname
                    DATA.append({"children": [], "name": '%s:%s' % (name, port)})
                keys = []
                mkey = 'op_redis_nexus_%s:%s' % (id, port)
                keys.append(mkey)
                for key in keys:
                    name = key.replace('op_redis_nexus_', '').split(':')
                    hostname = RC_CLUSTER.hget('op_server_hostnames',name[0])
                    if hostname:
                        name[0] = hostname
                    name = ':'.join(name)
                    if RC.exists(key):
                        for val in eval(RC.get(key)):
                            id, port = val
                            key = 'op_redis_nexus_%s:%s' % (id, port)
                            if RC.exists(key):
                                keys.append(key)
                            hostname = RC_CLUSTER.hget('op_server_hostnames',id)
                            if hostname:
                                id = hostname
                            for datas in DATA:
                                if datas['name'] == name:
                                    datas["children"].append({"children": [], "name": '%s:%s' % (id, port)})
                                else:
                                    for data in datas["children"]:
                                        if data['name'] == name:
                                            data["children"].append({"children": [], "name": '%s:%s' % (id, port)})
                                        else:
                                            for DAT in data["children"]:
                                                if DAT['name'] == name:
                                                    DAT["children"].append({"children": [], "name": '%s:%s' % (id, port)})
                                                else:
                                                    for dat in DAT["children"]:
                                                        if dat['name'] == name:
                                                            dat["children"].append({"children": [], "name": '%s:%s' % (id, port)})
                                                        else:
                                                            for da in dat["children"]:
                                                                if da['name'] == name:
                                                                    da["children"].append({"children": [], "name": '%s:%s' % (id, port)})
                                                                else:
                                                                    for dd in da["children"]:
                                                                        if dd['name'] == name:
                                                                            dd["children"].append({"children": [],"name": '%s:%s' % (id, port)})
                                                                        else:
                                                                            for d in dd["children"]:
                                                                                if d['name'] == name:
                                                                                    d["children"].append({"children": [],"name": '%s:%s' % (id, port)})
                                                                                else:
                                                                                    for t in d["children"]:
                                                                                        if t['name'] == name:
                                                                                            t["children"].append({"children": [],"name": '%s:%s' % (id, port)})
                tree = Tree(width='100%', height=600)
                tree.add("", DATA,tree_symbol_size=10,tree_label_text_size=14,tree_leaves_text_size=12,is_toolbox_show=False)
            except Exception as e:
                logging.error(e)
        return render_template('redis_status.html', BARS=BARS, hostname=hostname, app_port=app_port,tree = tree)
    except Exception as e:
        logging.error(e)

@page_app_service.before_request
@check.login_required(grade=1)
def check_login(error=None):
    produce.Async_log(g.user, request.url)

@page_app_service.teardown_request
def db_remove(error=None):
    db_op.DB.session.remove()
    db_idc.DB.session.remove()