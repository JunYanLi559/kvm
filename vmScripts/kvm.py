#!/usr/bin/python

import subprocess, datetime, os, sys
from os.path import basename
from RedisHelper import RedisHelper
import xml.etree.ElementTree as ET
import libvirt
import pymysql

def pub(vm_info):
    pub = RedisHelper()
    pub.publish(vm_info)


def sub():
    sub = RedisHelper()
    redis_sub = sub.subscribe()
    while True:
        global msg
        msg = redis_sub.parse_response()

def run_command(cmd):
    if type(cmd) == str:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    else:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    output, err = p.communicate()
    p_status = p.wait()
    result = {"out": output, "err": err, "exit_code": p_status}
    return result

if __name__ == "__main__":
    sub = RedisHelper()
    redis_sub = sub.subscribe()
    config={"host":"192.168.43.96",
            "user":"root",
            "password":"lijunyan",
            "database":"vm"
            }
    db=pymysql.connect(**config)
    while True:
        msg=redis_sub.parse_response()
        msg=msg[2].decode().split(",")
        if msg[-1]=="createVM":
            tree=ET.parse("/home/ljy/kvm_xml/vm1.xml")
            root=tree.getroot()
            name=root.find("name")
            name.text=  msg[0]
            cmd='cp /home/ljy/kvm_qcow2/vm1.qcow2 /home/ljy/kvm_qcow2/'+msg[0]+'.qcow2'
            os.system(cmd)
            vcpu=root.find("vcpu")
            vcpu.text=msg[1]
            mem=root.find("memory")
            cmem=root.find("currentMemory")
            cmem.text=str(int(msg[2])*1024*1024)
            mem.text=str(int(msg[2])*1024*1024)
            devices=root.find("devices")
            disk=devices.find("disk")
            source=disk.find("source")
            source.set("file",'/home/ljy/kvm_qcow2/'+msg[0]+'.qcow2')
            tree.write("/home/ljy/kvm_xml/"+msg[0]+'.xml')
            cmd='chmod -R 777 /home/ljy/kvm_xml'
            os.system(cmd)
            cmd='chmod -R 777 /home/ljy/kvm_qcow2'
            os.system(cmd)
            cmd='virsh define /home/ljy/kvm_xml/'+msg[0]+'.xml'
            os.system(cmd)
            cmd='virsh start '+msg[0]
            os.system(cmd)
            cursor=db.cursor()
            sql="INSERT INTO disk(disk_name,size,vm_name,stute) VALUES ('%s','%s','%s','used')"%(msg[0],str(int(msg[2])*1024*1024),msg[0])
            cursor.execute(sql)
            db.commit()
            cursor.close()
        elif msg[-1]=="listVM":
            conn=libvirt.open("qemu:///system")
            dom_list=conn.listDomainsID()
            list=[]
            for dom in dom_list:
                domain = conn.lookupByID(dom)
                name=domain.name()#name
                cpu=domain.maxVcpus()
                instance_memory = domain.memoryStats()
                total_memory = instance_memory["actual"]
                unused_memory = instance_memory["unused"]
                stute=domain.state()
                temp=name+'+'+str(cpu)+'+'+str(total_memory)+'+'+str(unused_memory)+"+running"
                list.append(temp)
            dom_list=conn.listDefinedDomains()
            for dom in dom_list:
                domain = conn.lookupByName(dom)
                name = domain.name()  # name
                temp = name + '+' + '---' + '+' + '---' + '+' + '---' + "+shutdown"
                list.append(temp)
            pub=RedisHelper()
            pub.publish(list)
        elif msg[-1]=='listDisk':
            cursor=db.cursor()
            sql='SELECT * FROM disk'
            cursor.execute(sql)
            data=cursor.fetchall()
            cursor.close()
            li=[]
            for i in range(len(data)):
                diskname=data[i][0]
                mem=str(data[i][1])
                if data[i][2]==None:
                    vmname='-'
                else:
                    vmname=data[i][2]
                state=data[i][3]
                temp=diskname+"~"+mem+"~"+vmname+"~"+state
                li.append(temp)
            pub=RedisHelper()
            pub.publish(li)
        elif msg[-1].split('~')[0]=='umount':
            opt=msg[-1].replace(' ','').split('~')
            disk_name=opt[1]
            vm_name=opt[2]
            cursor = db.cursor()
            sql = "SELECT * FROM disk WHERE disk_name='%s' "%(disk_name)
            cursor.execute(sql)
            data = cursor.fetchall()
            cursor.close()
            vm_name=data[0][2]
            cmd='virsh undefine '+vm_name
            os.system(cmd)
            cursor=db.cursor()
            sql="UPDATE disk SET vm_name=NULL,stute='unused' WHERE disk_name='%s'"%(disk_name)
            cursor.execute(sql)
            db.commit()
            cursor.close()
            cursor = db.cursor()
            sql = 'SELECT * FROM disk'
            cursor.execute(sql)
            data = cursor.fetchall()
            cursor.close()
            li = []
            for i in range(len(data)):
                diskname = data[i][0]
                mem = str(data[i][1])
                if data[i][2] == None:
                    vmname = '-'
                else:
                    vmname=data[i][2]
                state = data[i][3]
                temp = diskname + "~" + mem + "~" + vmname + "~" + state
                li.append(temp)
            pub = RedisHelper()
            pub.publish(li)
        elif msg[-1].split('~')[0]=='mount':
            opt = msg[-1].replace(' ','').split('~')
            disk_name = opt[1]
            vm_name = opt[2]
            #fix xml
            path="/home/ljy/kvm_xml/"+vm_name+".xml"
            tree = ET.parse(path)
            root = tree.getroot()
            devices = root.find("devices")
            disk = devices.find("disk")
            source = disk.find("source")
            source.set("file", '/home/ljy/kvm_qcow2/' + disk_name + '.qcow2')
            tree.write("/home/ljy/kvm_xml/" + vm_name + '.xml')
            cmd = 'chmod -R 777 /home/ljy/kvm_xml'
            os.system(cmd)
            #fix mysql
            cmd = 'virsh define '+path
            os.system(cmd)
            cursor = db.cursor()
            sql="UPDATE disk SET vm_name='%s',stute='used' WHERE disk_name='%s'"% (vm_name,disk_name)
            cursor.execute(sql)
            db.commit()
            cursor.close()
            cursor = db.cursor()
            sql = 'SELECT * FROM disk'
            cursor.execute(sql)
            data = cursor.fetchall()
            cursor.close()
            li = []
            for i in range(len(data)):
                diskname = data[i][0]
                mem = str(data[i][1])
                if data[i][2] == None:
                    vmname = '-'
                else:
                    vmname=data[i][2]
                state = data[i][3]
                temp = diskname + "~" + mem + "~" + vmname + "~" + state
                li.append(temp)
            pub = RedisHelper()
            pub.publish(li)
        elif msg[-1].split("~")[0]=='deldisk':
            opt=msg[-1].split('~')
            disk_name=opt[1].replace(' ','')
            path='/home/ljy/kvm_qcow2/'+disk_name+'.qcow2'
            cmd='rm -f '+path
            os.system(cmd)
            cursor = db.cursor()
            sql = "DELETE FROM disk WHERE disk_name='%s'" % (disk_name)
            cursor.execute(sql)
            db.commit()
            cursor.close()
            cursor = db.cursor()
            sql = 'SELECT * FROM disk'
            cursor.execute(sql)
            data = cursor.fetchall()
            cursor.close()
            li = []
            for i in range(len(data)):
                diskname = data[i][0]
                mem = str(data[i][1])
                if data[i][2] == None:
                    vmname = '-'
                state = data[i][3]
                temp = diskname + "~" + mem + "~" + vmname + "~" + state
                li.append(temp)
            pub = RedisHelper()
            pub.publish(li)

        elif msg[-1].split('~')[0]=="start":
            opt=msg[-1].split('~')
            vm_name=opt[1].replace(' ','')
            # conn=libvirt.open("qemu:///system")
            # dom=conn.lookupByName(vm_name)
            exit_code=0
            pub=RedisHelper()
            try:
                cmd="virsh start "+vm_name
                os.system(cmd)
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish("error")
        elif msg[-1].split('~')[0]=="shutdown":
            opt=msg[-1].split('~')
            vm_name=opt[1].replace(' ','')
            # conn=libvirt.open("qemu:///system")
            # dom=conn.lookupByName(vm_name)
            exit_code=0
            pub=RedisHelper()
            try:
                cmd='virsh shutdown '+vm_name
                os.system(cmd)
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish("error")
        elif msg[-1].split('~')[0]=="reboot":
            opt=msg[-1].split('~')
            vm_name=opt[1].replace(' ','')
            # conn=libvirt.open("qemu:///system")
            # dom=conn.lookupByName(vm_name)
            exit_code=0
            pub=RedisHelper()
            try:
                cmd='virsh reboot '+vm_name
                os.system(cmd)
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish("error")
        elif msg[-1].split('~')[0]=="suspend":
            opt=msg[-1].split('~')
            vm_name=opt[1].replace(' ','')
            conn=libvirt.open("qemu:///system")
            dom=conn.lookupByName(vm_name)
            exit_code=0
            pub=RedisHelper()
            try:
                dom.suspend()
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish("error")
        elif msg[-1].split('~')[0]=="resume":
            opt=msg[-1].split('~')
            vm_name=opt[1].replace(' ','')
            conn=libvirt.open("qemu:///system")
            dom=conn.lookupByName(vm_name)
            exit_code=0
            pub=RedisHelper()
            try:
                dom.resume()
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish("error")
        elif msg[-1].split('~')[0]=="alter":
            opt=msg[-1].split('~')
            vm_name=opt[1].replace(' ','')
            cpu=int(opt[2])
            ram=int(opt[3])
            conn=libvirt.open("qemu:///system")
            dom=conn.lookupByName(vm_name)

            exit_code=0
            pub=RedisHelper()
            if cpu > dom.maxVcpus() or ram > dom.maxMemory():
                exit_code = -1
            try:
                cmd='virsh setmem '+vm_name+" "+str(ram)+" --config --live"
                os.system(cmd)
                cmd='virsh setvcpus --config '+vm_name+' '+str(cpu)
                os.system(cmd)
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish("error")
        elif msg[-1].split('~')[0]=='createDisk':
            opt=msg[-1].split('~')
            diskname=opt[1]
            disksize=opt[2]
            cmd='cp /home/ljy/kvm_qcow2/vm1.qcow2 /home/ljy/kvm_qcow2/'+diskname+'.qcow2'
            os.system(cmd)
            disksize=int(disksize)
            add=disksize-7
            if add>=0:
                #add=str(add)
                cmd='qemu-img resize /home/ljy/kvm_qcow2/'+diskname+'.qcow2 '+"+%dG"%(add)
                os.system(cmd)
                pub=RedisHelper()
                strr=diskname+'~'+str(disksize)+'~'+'ok'
                cursor = db.cursor()
                sql = "INSERT INTO disk(disk_name,size,vm_name,stute) VALUES ('%s','%s','%s','unused')" % (diskname, str(int(disksize) * 1024 * 1024), '-')
                cursor.execute(sql)
                db.commit()
                pub.publish(strr)
            else:
                pub.publish('')

        elif msg[-1].split('~')[0]=='migrate':
            opt=msg[-1].split('~')
            ip=opt[1]
            vm_name=opt[2]
            conn=libvirt.open("qemu:///system")
            conn2=libvirt.open('qemu+tcp://kvm2@kvm2/system')
            dom=conn.lookupByName(vm_name)
            exit_code=0
            pub=RedisHelper()
            #cmd='virsh migrate %s qemu+tcp://%s/system --unsafe --persistent'%(vm_name,'kvm2')
            try:
                dom.migrate(conn2,True,vm_name,None,0)
                #os.system(cmd)
                #cmd='scp /home/ljy/kvm_xml/%s.xml ljy@kvm2:/home/ljy/kvm_xml/%s.xml'%(vm_name,vm_name)
                #os.system(cmd)
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish('error')
        elif msg[-1].split('~')[0] == 'delete':
            opt=msg[-1].split('~')
            vm_name=opt[1]
            conn=libvirt.open('qemu:///system')
            cmd='virsh undefine '+vm_name
            dom=conn.lookupByName(vm_name)
            exit_code=0
            pub=RedisHelper()
            try:
                #conn.lookupByName(vm_name)
                os.system(cmd)
            except:
                exit_code=-1
            if exit_code==0:
                pub.publish("ok")
            else:
                pub.publish("error")




