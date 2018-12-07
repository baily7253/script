# _*_ coding:utf8 _*_

import requests
import json
import sys
import os 
import yaml
import commands
import re
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
update_config=True

class OpenShift(object):

    def __init__(self):
        print('Welcome To OpenShift API ! ')
        self.serverurl = 'https://paas.yk.com:8443'
        self.namespace = sys.argv[1]
        self.dcname = sys.argv[2]
        self.imagename = sys.argv[3]
        self.podcount = sys.argv[4]
        self.servicename = self.dcname
        self.port = sys.argv[5]
        self.tport = sys.argv[6]
        self.token = 'Bearer ' + str(self.GetToken())
        self.headers = {'Authorization': self.token,'Accept':'application/json','Content-Type':'application/json'}

    #获取token
    def GetToken(self):
        #print('Get Token')
        response_type = 'code'
        client_id = 'openshift-browser-client'
        apipath=self.serverurl + '/oauth/authorize?' + 'response_type=' + response_type + '&client_id=' + client_id
        cmd = 'curl -k -X GET ' + "'" + apipath + "'" + ' -u testdeploy:1qaz@WSX -I -s'
        #print(cmd)
        status,response = commands.getstatusoutput(cmd)
        #print(response)
    
        if status != 0:
            print('Requests error !')
            return False
        else:
            pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            tokenurl = re.findall(pattern,response)[0]
            response = requests.get(tokenurl,verify=False).text
            #print(response)
            pattern = "<code>(.*?)</code>"
            token = re.findall(pattern,response)[0]
            if token == ' ':
                print('token error!')
                return False
            else:
                print('Get token success!')
            return token
    
    #创建registry证书
    def CreateSecret(self):
        apipath = self.serverurl + '/api/v1/namespaces/' + self.namespace + '/secrets'
        #print(apipath)
        response = requests.get(apipath,headers=self.headers,verify=False)
        secrets = json.loads(response.text)
        #print(secrets['items'][0]['metadata']['name'])
        secretlist = []
        for secret in secrets['items']:
            secretlist.append(secret['metadata']['name']) 
        if 'registry' in secretlist:
            print('>>>Registry secrets isexists')
            return True
        else:
            print('>>>Create Registry secrets......')
            #替换文件内容
            cmd1 = '''sed -i 's#test#''' + self.namespace + '#g' + "' registry.yaml" 
            os.system(cmd1)
            #读取配置
            f = open('registry.yaml')
            secretconfig = f.read()
            f.close()
            config = json.dumps(yaml.load(secretconfig))
            #create
            response = requests.post(apipath,data=config,headers=self.headers,verify=False)
            #print(response.status_code,response.text)
            if int(response.status_code) <= 300:
                print("    registry secret create success")
            else:
                print("    registry secret create error")

            return int(response.status_code)

    #获取DC
    def GetDcList(self):
        #print('Get DcList')
        apipath = self.serverurl + '/apis/apps.openshift.io/v1/namespaces/' + self.namespace + '/deploymentconfigs'
        response = requests.get(apipath,headers=self.headers,verify=False)
        #print(response.status_code,response.text)
        dclist = json.loads(response.text)
        dcs = []
        for dc in dclist['items']:
            dcs.append(dc['metadata']['name'])
        #print(dcs)
        if self.dcname in dcs:
            return True
        else:
            return False

    #更改dc配置
    def NewDcConfig(self,dcconfig):
        if self.podcount != '':
           dcconfig['spec']['replicas'] = self.podcount
        else:
            print('Use default pod config --->1')
        dcconfig['spec']['template']['spec']['containers'][0]['image'] = self.imagename
        
        #configmap
        if update_config == True:
            apipath = self.serverurl + '/api/v1/namespaces/' + self.namespace + '/configmaps'
            response = requests.get(apipath,headers=self.headers,verify=False)
            #print(response.status_code,response.text)
            configmaps = json.loads(response.text)
            cps = []
            for config in configmaps['items']:
                cps.append(config['metadata']['name'])
            if self.dcname in cps:
                print('configMap is exists')
                keylist=[]
                for key in dcconfig['spec']['template']['spec']['volumes']:
                    keylist.extend(key.keys())
                print(keylist)
                if 'configMap' in keylist:
                    print('already mount configmap')
                else:
                    print('add configmap !')
                    mountinfo = {'readOnly': True, 'mountPath': '/config', 'name': self.dcname}
                    configinfo = {'configMap': {'defaultMode': 420, 'name': self.dcname}, 'name': self.dcname}
                    dcconfig['spec']['template']['spec']['containers'][0]['volumeMounts'].append(mountinfo)
                    dcconfig['spec']['template']['spec']['volumes'].append(configinfo)
            else:
                print('configMap is not exists')
                
        data = json.dumps(dcconfig)
        return data

    #更改service配置
    def NewServiceConfig(self,serviceconfig):
        if serviceconfig['spec']['ports'][0]['port'] == int(self.port):
            pass
        else:
            serviceconfig['spec']['ports'][0]['port'] = int(self.port)
        if serviceconfig['spec']['ports'][0]['targetPort'] == int(self.tport):
            pass
        else:
            serviceconfig['spec']['ports'][0]['targetPort'] = int(self.tport)
        data = json.dumps(serviceconfig)
        return data

    #创建DC
    def CreateDC(self):
        #print("Create NewDc!")
        apipath = self.serverurl + '/apis/apps.openshift.io/v1/namespaces/' + self.namespace + '/deploymentconfigs/'
        #替换文件内容
        cmd1 = '''sed -i 's#test#''' + self.namespace + '#g' + "' default.yaml" 
        cmd2 = '''sed -i 's#springboot-server#''' + self.dcname + '#g' + "' default.yaml"
        os.system(cmd1 + "&&" + cmd2)
        #yaml to dict
        f = open('default.yaml')
        dcconfig = f.read()
        f.close()
        dictconfig = yaml.load(dcconfig)
        #更新镜像
        newconfig = self.NewDcConfig(dictconfig)
        #开始创建
        response = requests.post(apipath,data=newconfig,headers=self.headers,verify=False)
        #print(response.status_code,response.text)
        return int(response.status_code)

    #更新DC
    def UpdateDC(self):
        apipath = self.serverurl + '/apis/apps.openshift.io/v1/namespaces/' + self.namespace + '/deploymentconfigs/' + self.dcname
        #upconfig = self.serverurl + '/apis/apps.openshift.io/v1/namespaces/' + self.namespace + '/deploymentconfigs/' + self.dcname
        dcconfig = json.loads(requests.get(apipath,headers=self.headers,verify=False).text)
        newconfig = self.NewDcConfig(dcconfig)
        response = requests.put(apipath,data=newconfig,headers=self.headers,verify=False)
        return int(response.status_code)

    #创建service
    def CreateService(self):
        #print("Strart create service", self.servicename)
        apipath = self.serverurl + '/api/v1/namespaces/' + self.namespace + '/services/'
        #替换文件内容
        cmd1 = '''sed -i 's#bigdata-stg#''' + self.namespace + '#g' + "' service.yaml" 
        cmd2 = '''sed -i 's#eureka02#''' + self.dcname + '#g' + "' service.yaml"
        os.system(cmd1 + "&&" + cmd2)
        #yaml to dict
        f = open('service.yaml')
        dcconfig = f.read()
        f.close()
        dictconfig = yaml.load(dcconfig)
        #更新镜像
        newconfig = self.NewServiceConfig(dictconfig)
        #开始创建
        response = requests.post(apipath,data=newconfig,headers=self.headers,verify=False)
        #print(response.status_code,response.text)
        return int(response.status_code)

    #更新service
    def UpdataService(self):
        apipath = self.serverurl + '/api/v1/namespaces/' + self.namespace + '/services/' + self.servicename
        serviceconfig = json.loads(requests.get(apipath,headers=self.headers,verify=False).text)
        newconfig = self.NewServiceConfig(serviceconfig)
        response = requests.put(apipath,data=newconfig,headers=self.headers,verify=False)
        return int(response.status_code)

    def GetPodNamesBefore(self):
        # 获取所有的pod名称
        apiPath = self.serverurl + '/api/v1/namespaces/' + self.namespace + '/pods/'
        response = requests.get(apiPath, headers=self.headers, verify=False)
        data = json.loads(response.text)
        podNames = []
        for pod in data['items']:
            if re.match(self.dcname, pod['metadata']['name']) != None:
                podNames.append(pod['metadata']['name'])

        return podNames

    def GetPodNamesAfter(self):
        # 获取所有的pod名称
        time.sleep(30)
        apiPath = self.serverurl + '/api/v1/namespaces/' + self.namespace + '/pods/'
        response = requests.get(apiPath, headers=self.headers, verify=False)
        data = json.loads(response.text)
        podNames = []
        for pod in data['items']:
            if re.match(self.dcname, pod['metadata']['name']) != None:
                podNames.append(pod['metadata']['name'])

        return podNames

    def GetPodIPs(self,podNamesFiltered):
        apiPath = self.serverurl + '/api/v1/namespaces/' + self.namespace + '/pods/'
        response = requests.get(apiPath, headers=self.headers, verify=False)
        data = json.loads(response.text)
        podIPs = []
        for podFiltered in podNamesFiltered:
            response = requests.get(apiPath + podFiltered, headers=self.headers, verify=False)
            result = json.loads(response.text)
            podIPs.append(result['status']['podIP'])

        return podIPs

    #DC controler
    def main(self):
        if self.token != False:
            time.sleep(2)
            self.CreateSecret()
            result = self.GetDcList()
            if result == True:
                podNamesBefore=self.GetPodNamesBefore()
                print('>>>DC (%s) exists' %(self.dcname,))
                print('    Start Update......')
                udcstatus = self.UpdateDC()
                if udcstatus <= 300:
                    print('    DC update success')
                else:
                    print('    DC update failed ')
                uservice = self.UpdataService()
                if uservice  <= 300:
                    print('    Service update success')
                else:
                    print('    Service update failed')
                podNamesAfter=self.GetPodNamesAfter()
                podNamesFiltered=[]
                for podAfter in podNamesAfter:
                    if podAfter not in podNamesBefore and "deploy" not in podAfter:
                        podNamesFiltered.append(podAfter)

                podIPs=self.GetPodIPs(podNamesFiltered)
                print(podIPs)

            elif result == False:
                print('>>>DC (%s) not exists' %(self.dcname,))
                print('    Start Create......')
                cdcstatus = self.CreateDC()
                if cdcstatus <= 300:
                    print('    DC create success')
                else:  
                    print('    DC create failed ')
                cservice = self.CreateService()
                if cservice  <= 300:
                    print('    Service create success')
                else:
                    print('    Service create failed')
                podNames = self.GetPodNamesAfter()
                podNamesFiltered = []
                for pod in podNames:
                    if  "deploy" not in pod:
                        podNamesFiltered.append(pod)

                podIPs = self.GetPodIPs(podNamesFiltered)
                print(podIPs)

        else:
            print("Get token failed ！")


if __name__ == '__main__':
    server = OpenShift()
    server.main()
 