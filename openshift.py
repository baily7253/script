# _*_ coding:utf-8 _*_

import requests
import json
import sys
import os 
import yaml
import commands
import re
from requests.packages.urllib3.exceptions import InsecureRequestWarning


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def Helper():
    print(" ---->>[python openshift.py runtype namespace dcname imagename podcount]  ")
    return True

def TestConnect():
    apiPath = serverUrl + '/apis/apps.openshift.io/v1/namespaces/' + namespace + '/deploymentconfigs'
    response = requests.get(apiPath,headers=headers,verify=False)
    dcList = json.loads(response.text)
    print(dcList)
    return True
    
#获取token
def GetToken(serverUrl):
    print('Get Token')
    cmd = 'curl -k -X GET ' + "'" + serverUrl +'/oauth/authorize?response_type=code&client_id=openshift-browser-client' + "'"  + ' -u testdeploy:1qaz@WSX -I -s'
    status,response = commands.getstatusoutput(cmd)
    if status != 0:
        print('Requests error !')
        return ' '
    else:
        pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        tokenUrl = re.findall(pattern,response)[0]
        response = requests.get(tokenUrl,verify=False).text
        #print(response)
        pattern = "<code>(.*?)</code>"
        token = re.findall(pattern,response)[0]
        if token == ' ':
            print('token error!')
            return ''
        else:
            print('Get token success!')
    return token

#获取NS下所有DC
def GetDcList(namespace,dcname):
    print('>>>Dc isexists')
    apiPath = serverUrl + '/apis/apps.openshift.io/v1/namespaces/' + namespace + '/deploymentconfigs'
    response = requests.get(apiPath,headers=headers,verify=False)
    #print(response.status_code,response.text)
    dcList = json.loads(response.text)
    dcs = []
    for dc in dcList['items']:
        dcs.append(dc['metadata']['name'])

    if dcname in dcs:
        print('true')
        return True
    else:
        print('false')
        return False

#获取DC配置
def GetDConfig(namespace,dcname):
    print('>>>Get DC Config')
    apiPath = serverUrl + '/apis/apps.openshift.io/v1/namespaces/' + namespace + '/deploymentconfigs/' + dcname
    response = requests.get(apiPath,headers=headers,verify=False)
    #print(response.status_code,response.text)
    return response.text

#创建新DC
def CreateDC(namespace,dcname,dcconfig):
    print(">>>Start Create DC !")
    apiPath = serverUrl + '/apis/apps.openshift.io/v1/namespaces/' + namespace + '/deploymentconfigs/'
    #替换文件内容
    nameSpaceCmd = '''sed -i 's#test#''' + namespace + '#g' + "' default.yaml" 
    dcNameCmd = '''sed -i 's#springboot-server#''' + dcname + '#g' + "' default.yaml"
    os.system(dcNameCmd + "&&" + nameSpaceCmd)
    #yaml to dict
    f = open(dcconfig)
    dcConfig = f.read()
    f.close()
    dictConfig = yaml.load(dcConfig)
    #更新镜像
    newConfig = NewDcConfig(imagename,podcount,dictConfig)
    #开始创建
    response = requests.post(apiPath,data=newConfig,headers=headers,verify=False)
    #print(response.status_code,response.text)


#更新DC
def UpdateDC(namespace,dcname,dcconfig):
    apiPath = serverUrl + '/apis/apps.openshift.io/v1/namespaces/' + namespace + '/deploymentconfigs/' + dcname
    response = requests.put(apiPath,data=dcconfig,headers=headers,verify=False)
    return True
 

#更改配置
def NewDcConfig(imagename,podcount,dcconfig):
    if podcount != '':
       dcconfig['spec']['replicas'] = int(podcount)
    else:
        print('Use default pod config --->1')
    dcconfig['spec']['template']['spec']['containers'][0]['image'] = imagename
    data = json.dumps(dcconfig)
    return data


if __name__ == '__main__':
    Helper()
    ##参数定义
    runtype = sys.argv[1]
    namespace = sys.argv[2]
    dcname = sys.argv[3]
    imagename = sys.argv[4]
    podcount = sys.argv[5]
    #环境类型
    if runtype == 'PRD':
       serverUrl = 'https://paas.uat.xxx.com:8443'
    else :
       serverUrl = 'https://paas.yk.com:8443'
    token = GetToken(serverUrl) 
    serverToken = 'Bearer ' + str(token)
    #print(serverToken)
    headers = {'Authorization': serverToken,'Accept':'application/json','Content-Type':'application/json'}
    result = GetDcList(namespace,dcname)
    if result == True:
        config = GetDConfig(namespace,dcname)
        dictConfig = json.loads(config)
        newConfig = NewDcConfig(imagename,podcount,dictConfig)
        UpdateDC(namespace,dcname,newConfig)
    elif result == False:
        CreateDC(namespace,dcname,'default.yaml')