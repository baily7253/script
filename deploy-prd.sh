#!/bin/bash
deployFlag=""
serviceJenkinsBuildUrl=""
#mysql数据库信息
mysql_host="127.0.0.1"
mysql_port="3306"
mysql_user="root"
mysql_password="Sonar@01"
mysql_dbname="devops_deploy"
#jenkins 账户信息
jenkins_username="itservice"
jenkins_passwd="Saic2107"
#根据service名字获取jenkins上对应的构建job
function getServiceBuildUrl(){
select_sql="select job_prd_url  from devops_deploy.service_list where service_name='$1';"
    mysql -h${mysql_host} -P${mysql_port}  -u${mysql_user}  -p${mysql_password}  -N  -e "${select_sql}" > ./tmp/serviceJenkinsBuildUrl.txt
    echo `cat ./tmp/serviceJenkinsBuildUrl.txt`
}
#根据service名字获取数据库中是否有对应数据
function getServiceCountFromDb(){
    select_sql="select count(*)  from devops_deploy.service_list where service_name='$1';"
    mysql -h${mysql_host} -P${mysql_port}  -u${mysql_user}  -p${mysql_password}  -N  -e "${select_sql}"  > ./tmp/serviceCount.txt
    echo `cat ./tmp/serviceCount.txt`
}
#获取是否触发回归接口测试flag  0为触发，1为不触发
function getServiceFlagFromDb(){
    select_sql="select interfacetest_flag from devops_deploy.service_list where service_name='$1';"
    mysql -h${mysql_host} -P${mysql_port}  -u${mysql_user}  -p${mysql_password}  -N  -e "${select_sql}"  > ./tmp/serviceFlag.txt
    echo `cat ./tmp/serviceFlag.txt`
}
#触发jenkins构建
function triggerJenkinsBuild(){
    echo "$1/buildWithParameters?delay=0sec"
    curl -X POST "$1/buildWithParameters?delay=0sec"  --user $jenkins_username:$jenkins_passwd --silent -d dockerTag=$2 
}

#获取job构建状态，true/false eg: http://jenkins.yk.com:8080/job/common-code-service/lastBuild/api/json
function getBuildStatus(){
    echo `curl -u $jenkins_username:$jenkins_passwd  $1/lastBuild/api/json --silent  | jq  .building `
}
#获取job构建结果，SUCCESS
function getBuildResult(){
    echo `curl -u $jenkins_username:$jenkins_passwd  $1/lastBuild/api/json --silent | jq '.result' |sed 's/\"//g'`
}
function getCurrentBuildDockerTag(){
    date=`date "+%Y"`
    echo `curl -u itservice:Saic2107 $1/lastBuild/api/json  --silent | jq  '.actions[0].parameters[].value' | sed 's/\"//g' | grep "$date" `
}


#获取之前已部署的应用
function getDeployedServices(){
    select_sql="select service_name  from devops_deploy.prd_result where deploy_flag=0;"
    mysql -h${mysql_host} -P${mysql_port}  -u${mysql_user}  -p${mysql_password}  -N  -e "${select_sql}"  > ./tmp/deployedServices.txt
    echo `cat ./tmp/deployedServices.txt`

}
#获取已部署应用的个数
function getDeployedServicesCount(){
    select_sql="select count(0)  from devops_deploy.prd_result where deploy_flag=0;"
    mysql -h${mysql_host} -P${mysql_port}  -u${mysql_user}  -p${mysql_password}  -N  -e "${select_sql}"  > ./tmp/deployedServicesCount.txt
    echo `cat ./tmp/deployedServicesCount.txt`

}

#插入数据
function insertResult(){
    insert_time=`date "+%Y-%m-%d %H:%M:%S"`
    insert_sql="INSERT INTO devops_deploy.prd_result(service_name,insert_time,deploy_flag,docker_tag) VALUES('$1','$insert_time',0,$2)"
    mysql -h${mysql_host} -P${mysql_port}  -u${mysql_user}  -p${mysql_password}  -N  -e "${insert_sql}" 

}
#更新数据,全部部署完成，添加结束标识方便后续部署
function updateResultFlag(){
    update_time=`date "+%Y-%m-%d %H:%M:%S"`
    update_sql="UPDATE devops_deploy.prd_result SET deploy_flag = '1' ,update_time = '$update_time' WHERE deploy_flag = '0' "
    mysql -h${mysql_host} -P${mysql_port}  -u${mysql_user}  -p${mysql_password}  -N  -e "${update_sql}" 

}


#判断是否执行成功
functionResult=""
function isExecSuccessful(){
    if [ $? = 0 ];then
        echo "0"
    fi
}

#判断服务是否在已部署的txt列表中
function  getDeployFlag(){
    grep $1  $2  > /dev/null
    if [ $? -eq 0 ]; then
        deployFlag="true"
    else
        deployFlag="false"
    fi
    echo $deployFlag
}
#循环时间
sleep_time=10
isBuilding=true
buildResult=""
#判断当前jenkins中是否包含所有job
for deployServiceInfo  in $(cat $1)
do
    deployService=(${deployServiceInfo//,/ }[0])
    serviceCount=`getServiceCountFromDb $deployService`
    if [[ $serviceCount -eq 1 ]]; then
        echo ''     
    elif [[ $serviceCount -gt 1 ]]; then
        echo "${deployService}在数据库中超过1条记录"
        exit 1
    else
        echo "${deployService}在数据库中没有记录"
        exit 2
    fi
done


#开始执行job

#获取已部署应用到本地
getDeployedServices

echo "------------------开始执行部署-----------------"
for deployServiceInfo  in $(cat $1)
do
    OLD_IFS="$IFS"
    IFS=","
    arr=($deployServiceInfo)
    IFS="$OLD_IFS"
    deployService=${arr[0]}
    dockerTag=${arr[1]}
    deployedFlag=`getDeployFlag  $deployService ./tmp/deployedServices.txt`
    
    if [[ "true" == "$deployedFlag" ]];then
        echo "-----------------$deployService已部署--------------------"        
    elif [[ "false" == "$deployedFlag" ]]; then
        serviceJenkinsBuildUrl=`getServiceBuildUrl $deployService`
        echo "------------------部署jenkins job为：$deployService($serviceJenkinsBuildUrl)-----------------"
        echo -e "\033[32m --------------------开始部署$deployService-------------------- \033[0m" 
        # eg：serviceJenkinsBuildUrl ：http://jenkins.yk.com:8080/job/common-code-service/
        triggerJenkinsBuild $serviceJenkinsBuildUrl $dockerTag
        sleep 20
        #执行完毕部署后，每隔10秒循环获取构建是否完成
        while  true  
        do
            isBuilding=`getBuildStatus $serviceJenkinsBuildUrl`
            echo -e  "\033[32m......\c\033[0m"
            if [ "false" = "$isBuilding" ];then
                break;
            fi
            sleep 20
        done
        #构建完成标识为false时，判断构建结果是否成功，如果成功则插入数据到mysql中，如果失败结束任务
        currentJobBuildResult=`getBuildResult  $serviceJenkinsBuildUrl`

        if [[ "SUCCESS" == "$currentJobBuildResult" ]]; then
            echo -e  "\033[32m --------------------$deployService部署成功!--------------------  \033[0m"
            #插入记录到result表中
            #insertResult $deployService
            echo "$deployService 部署成功，当前构建docker镜像版本号为：$dockerTag"
            insertResult $deployService $dockerTag
            echo "$deployService,$dockerTag" >> report.txt
            sleep 10
        else
            echo -e "\033[31m -------------------$deployService部署失败，请解决报错后继续执行！------------------- \033[0m"
            exit 3
        fi
    else
        echo "未知错误"
        exit 4
    fi                
done
deployedSum=`getDeployedServicesCount`
#检查
echo -e "\033[32m ------------------部署总个数： $deployedSum------------------- \033[0m"
#当前部署完成后flag全部置为1
updateResultFlag
mv report.txt ./history/`date "+%Y%m%d%H%M"`-report-prd.txt
#执行接口测试，需判断当前部署服务中是否有触发回归测试的flag
interfaceTestFlag=''
for deployService  in $(cat $1)
do
    deployService=(${deployService//,/ }[0])
    interfaceTestFlag=`getServiceFlagFromDb $deployService`
    if [[ $interfaceTestFlag == "0" ]]; then
        break;
    fi
done
echo "是否满足执行测试条件：$interfaceTestFlag (0为触发，1为不触发)"
if [[ $interfaceTestFlag == "0" ]]; then
    echo "===========执行接口测试==========="
else
    echo "当前部署的服务中没有需要触发回归测试的服务！跳过测试！"
fi
#删除临时文本文件
rm -f ./tmp/*