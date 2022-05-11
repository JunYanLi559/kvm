import threading

from flask import Flask, render_template, request, redirect, make_response, session,url_for
from datetime import timedelta
from RedisHelper import RedisHelper
from time import sleep
import re
app = Flask(__name__)
app.secret_key = 'kvm'
app.permanent_session_lifetime = timedelta(minutes=30)
msg = []


def pub(vm_info):
    pub = RedisHelper()
    pub.publish(vm_info)


def sub():
    sub = RedisHelper()
    redis_sub = sub.subscribe()
    while True:
        global msg
        msg = redis_sub.parse_response()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if (username == 'kvm' and password == '123456'):
            response = make_response(redirect('/index'))
            response.set_cookie('username', value=username, max_age=300)
            session['islogin'] = '1'
            return response
        else:
            session['islogin'] = '0'
            return "账号或密码错误"
    else:
        session['islogin'] = '0'
        return render_template('login.html')


@app.route('/index', methods=['GET', 'POST'])
def index():
    username = request.cookies.get('username')
    if not username:
        return "请登录!"
    islogin = session.get('islogin')
    if request.method == 'POST':
        response = make_response(redirect('/createVM'))
        response.set_cookie('username', value=username, max_age=10000)
        session['islogin'] = '1'
        return response
    else:
        return render_template('index.html', username=username, islogin=islogin)



@app.route('/createVM',methods=['GET','POST'])
def createVM():
    if request.method=='POST':
        vm_name=request.form.get('vm_name')
        vm_cpu=request.form.get('vm_cpu')
        vm_memory=request.form.get('vm_memory')
        vm_disk= request.form.get('vm_disk')
        vm_images=request.form.get('vm_images')
        vm_info=[vm_name,vm_cpu,vm_memory,vm_disk,vm_images]
        threads=[]
        t1=threading.Thread(target=sub)
        threads.append(t1)
        t2=threading.Thread(target=pub, args=(vm_info,))
        threads.append(t2)
        for t in threads:
            t.setDaemon(True)
            t.start()
        sleep(2)
        if len(msg)>1:
            print(msg[2])
            msg[2]=msg[2].decode()
            info = re.findall("'([^']*)'", msg[2])
            vm_name = info[0]
            cpu = info[1]
            mem = info[2]
            os_type = info[3]
            vm_info = vm_name + "," + cpu + "," + mem + "," + os_type
            pub(vm_info+","+"createVM")
            return "%s is created!" % (vm_info)
        else:
            session['islogin'] = '0'
            return "密码或用户名错误"
    else:
        username = request.cookies.get('username')
        if not username:
            return "请登录"
        islogin = session.get('islogin')
        return render_template('createVM.html', username=username, islogin=islogin)
@app.route('/listVM')
def listVM():
    url = request.args.get('url')
    global vm_list
    global vm_info
    vm_list = []
    if url != None:
        response = make_response(redirect('/url'))
        response.set_cookie('url', value=url)
        return response
    else:
        username=request.cookies.get('username')
        pub("listVM")
        sub=RedisHelper()
        redis_sub=sub.subscribe()
        while True:
            msg=redis_sub.parse_response()
            #msg = msg.decode().split(",")
            print(msg)
            massage=msg[-1].decode()
            if massage=='listVM':
                continue
            else:
                vm_info=msg[2].decode()
                print(vm_info)
                break
        vm_info=vm_info.replace('[','').replace(']','')
        vm_info=vm_info.split(',')
        for info in vm_info:
            temp=info.split('+')
            l = []
            for i in temp:
                i=i.replace('\'','')
                l.append(i)
            vm_list.append(l)
        if not username:
            return "请登录"
        islogin=session.get("islogin")
        return render_template("listVM.html",username=username,islogin=islogin,vm_info=vm_list)

@app.route('/detailVM',methods=['GET','POST'])
def detailVM():
    username=request.cookies.get('username')
    vm_info=request.args.get('vm_name')
    vm_info=vm_info.replace('[','').replace(']','')
    vm_info=vm_info.split(',')
    if not username:
        return "请登录"
    islogin=session.get('islogin')
    if request.method=='POST':
        cpu=request.form.get('cpu')
        ram=request.form.get('ram')
        if cpu==None and ram==None:
            operatevm=request.form.get('oprate_vm')
            oprate=operatevm.split('~')[0]
            if oprate=='start':
                pub(operatevm)
                sub=RedisHelper()
                redis_sub=sub.subscribe()
                while True:
                    msg=redis_sub.parse_response()
                    massage=msg[-1]
                    if massage=='start':
                        continue
                    else:
                        massage=massage.decode()
                        if massage=='ok':
                            vm_info[-1]='running'
                        else:
                            return "error"
                        break
                return render_template('detailVM.html',username=username,islogin=islogin,vm=vm_info)
            elif oprate=="shutdown":
                pub(operatevm)
                sub=RedisHelper()
                redis_sub=sub.subscribe()
                while True:
                    msg = redis_sub.parse_response()
                    massage = msg[-1]
                    if massage == 'shutdown':
                        continue
                    else:
                        massage = massage.decode()
                        if massage == 'ok':
                            vm_info[-1] = 'shutdown'
                        else:
                            return "error"
                        break
                return render_template('detailVM.html', username=username, islogin=islogin, vm=vm_info)
            elif oprate=="reboot":
                pub(operatevm)
                sub=RedisHelper()
                redis_sub=sub.subscribe()
                while True:
                    msg = redis_sub.parse_response()
                    massage = msg[-1]
                    if massage == 'reboot':
                        continue
                    else:
                        massage = massage.decode()
                        if massage == 'ok':
                            vm_info[-1] = 'running'
                        else:
                            return "error"
                        break
                return render_template('detailVM.html', username=username, islogin=islogin, vm=vm_info)
            elif oprate=='suspend':
                pub(operatevm)
                sub = RedisHelper()
                redis_sub = sub.subscribe()
                while True:
                    msg = redis_sub.parse_response()
                    massage = msg[-1]
                    if massage == 'suspend':
                        continue
                    else:
                        massage = massage.decode()
                        if massage == 'ok':
                            vm_info[-1] = 'suspend'
                        else:
                            return "error"
                        break
                return render_template('detailVM.html', username=username, islogin=islogin, vm=vm_info)
            elif oprate=='resume':
                pub(operatevm)
                sub = RedisHelper()
                redis_sub = sub.subscribe()
                while True:
                    msg = redis_sub.parse_response()
                    massage = msg[-1]
                    if massage == 'resume':
                        continue
                    else:
                        massage = massage.decode()
                        if massage == 'ok':
                            vm_info[-1] = 'running'
                        else:
                            return "error"
                        break
                return render_template('detailVM.html', username=username, islogin=islogin, vm=vm_info)
        else:
            alter_name=request.form.get('alter_name')
            alter_args="alter"+"~"+alter_name+"~"+cpu+"~"+ram
            pub(alter_args)
            sub=RedisHelper()
            redis_sub=sub.subscribe()
            while True:
                msg = redis_sub.parse_response()
                massage = msg[-1]
                if massage=='alter':
                    continue
                else:
                    massage = massage.decode()
                    if massage=='ok':
                        vm_info[1]=cpu
                        vm_info[2]=ram
                    else:
                        return "must be smaller than allowable"
                    break
            return render_template('detailVM.html', username=username, islogin=islogin, vm=vm_info)
    else:
         return render_template('detailVM.html', username=username, islogin=islogin, vm=vm_info)
@app.route("/url",methods=['GET','POST'])
def url():
    if request.method=='POST':
        username=request.cookies.get('username')
        islogin=session.get('islogin')
        ip=request.form.get('ip')
        link='http://'+ip+':6080/vnc.html'
        return render_template("url.html", username=username, islogin=islogin,url=link)
    else:
        username = request.cookies.get('username')
        if not username:
            return "请登录"
        islogin = session.get("islogin")
        return render_template("url.html", username=username, islogin=islogin)
@app.route("/migrateVM",methods=['GET','POST'])
def migrateVM():
    if request.method=='POST':
        vm_name=request.form.get('vm_name')
        KVM_IP=request.form.get('kvm_ip')
        migrate_info="migrate~"+KVM_IP+"~"+vm_name
        pub(migrate_info)
        sub=RedisHelper()
        redis_sub=sub.subscribe()
        status="failure"
        while True:
            msg=redis_sub.parse_response()
            if msg[-1].decode().split("~")[0]=='migrate':
                continue
            else:
                status=msg[-1].decode()
                break
        if status=='ok':
            response=make_response(redirect('/migrated'))
            result=vm_name+"~"+status
            response.set_cookie('result',value=result)
            return response
        elif status=='failure':
            response=make_response(redirect('/migrated'))
            result=vm_name+"~"+status
            response.set_cookie('result',value=result)
            return response
    else:
        username=request.cookies.get('username')
        if not username:
            return "请登录"
        islogin = session.get("islogin")
        return render_template("migrateVM.html", username=username, islogin=islogin)

@app.route("/migrated")
def migrated():
    username=request.cookies.get('username')
    result=request.cookies.get('result')
    if not username:
        return "请登录"
    islogin = session.get("islogin")
    return render_template("migrated.html", username=username, islogin=islogin,result=result)
@app.route("/deleteVM",methods=['POST','GET'])
def deleteVM():
    if request.method == 'POST':
        vm_name = request.form.get('vm_name')
        vm_info = "delete~"+vm_name
        pub(vm_info)
        sub=RedisHelper()
        redis_sub=sub.subscribe()
        while True:
            msg = redis_sub.parse_response()
            massage = msg[-1]
            if massage == 'delete':
                continue
            else:
                massage = massage.decode()
                if massage == 'ok':
                    return "delete finished"
                else:
                    return "error"
                break
        return render_template('deleteVM.html', username=username, islogin=islogin)
    else:
        username = request.cookies.get('username')
        if not username:
            return "请登录"
        islogin = session.get('islogin')
        return render_template('deleteVM.html', username=username, islogin=islogin)
@app.route('/listDisk',methods=['GET','POST'])
def listDisk():
    global disk_info
    disk_list=[]
    if request.method=='POST':
        disk_mount_unmount=request.form.get('mount_umount')
        if disk_mount_unmount!=None:
            username=request.cookies.get('username')
            if disk_mount_unmount.split("~")[0]=='umount':
                pub(disk_mount_unmount)
                sub=RedisHelper()
                redis_sub=sub.subscribe()
                while True:
                    msg=redis_sub.parse_response()
                    opt=msg[-1].decode()
                    if opt.split("~")[0]=='umount':
                        continue
                    else:
                        disk_info = opt.replace('[', '').replace(']', '').replace('\'', '').split(",")
                        break
                for i in range(len(disk_info)):
                    info = disk_info[i].split('~')
                    disk_list.append(info)
                if not username:
                    return "请登录"
                islogin = session.get('islogin')
                return render_template('listDisk.html', username=username, islogin=islogin, disk_info=disk_list)
            elif disk_mount_unmount.split('~')[0]=='deldisk':
                disk_del=disk_mount_unmount
                pub(disk_del)
                sub=RedisHelper()
                redis_sub=sub.subscribe()
                while True:
                    msg = redis_sub.parse_response()
                    opt = msg[-1].decode()
                    if opt.split("~")[0] == 'deldisk':
                        continue
                    else:
                        disk_info = opt.replace('[', '').replace(']', '').replace('\'', '').split(",")
                        break
                for i in range(len(disk_info)):
                    info = disk_info[i].split('~')
                    disk_list.append(info)
                if not username:
                    return "请登录"
                islogin = session.get('islogin')
                return render_template('listDisk.html', username=username, islogin=islogin, disk_info=disk_list)
            else:
                vm_name=request.form.get('mount_disk_name')
                opt=vm_name.split("~")[0]
                vm_name=vm_name+"~"+disk_mount_unmount
                pub(vm_name)
                sub = RedisHelper()
                redis_sub = sub.subscribe()
                while True:
                    msg = redis_sub.parse_response()
                    opt = msg[-1].decode()
                    if opt.split("~")[0] == 'mount':
                        continue
                    else:
                        disk_info = opt.replace('[', '').replace(']', '').replace('\'', '').split(",")
                        break
                for i in range(len(disk_info)):
                    info = disk_info[i].split('~')
                    disk_list.append(info)
                if not username:
                    return "请登录"
                islogin = session.get('islogin')
                return render_template('listDisk.html', username=username, islogin=islogin, disk_info=disk_list)
    else:
        username=request.cookies.get('username')
        pub('listDisk')
        sub=RedisHelper()
        redis_sub=sub.subscribe()
        while True:
            msg=redis_sub.parse_response()
            temp=msg[-1].decode()
            if temp=='listDisk':
                continue
            else:
                disk_info=temp.replace('[','').replace(']','').replace('\'','').split(",")
                break
        for i in range(len(disk_info)):
            info=disk_info[i].split('~')
            disk_list.append(info)
        if not username:
            return "请登录"
        islogin=session.get('islogin')
        return render_template('listDisk.html',username=username,islogin=islogin,disk_info=disk_list)
@app.route('/createDisk',methods=['GET','POST'])
def createDisk():
    if request.method == 'POST':
        disk_name = request.form.get('disk_name')
        disk_size = request.form.get('disk_size')
        disk_info = 'createDisk~'+str(disk_name)+'~'+str(disk_size)
        pub(disk_info)
        sub = RedisHelper()
        redis_sub = sub.subscribe()
        status = "failure"
        while True:
            msg = redis_sub.parse_response()
            temp=msg[-1].decode()
            temp=temp.split('~')
            if temp[0]=='createDisk':
                continue
            else:
                status=temp[-1]
                break
        if status == "ok":
            return "%s is created %s!" % (disk_name, status)
        else:
            return "%s is created %s!" % (disk_name, status)

    else:
        username = request.cookies.get('username')
        if not username:
            return "please login!!!"
        islogin = session.get('islogin')
        return render_template('createDisk.html', username=username, islogin=islogin)

if __name__=="__main__":
    app.run(host="0.0.0.0")