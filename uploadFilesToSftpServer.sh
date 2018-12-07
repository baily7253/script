#!/bin/bash
ftpIp='10.118.80.7'
ftpUsername='uploadwar'
ftpPwd='uploadwar'
ftpPort='22'
secretDir=/home/jenkins/.ssh/id_rsa

#参数说明
#$1   上传类型，1,2,3
#$2   ftp远端目录，对应jenkins ftpDirectory
#$3   上传的目录名称，对应jenkins moduleName
#$4   用于指定ftp目录上时间戳，与moduleName拼接成目录名
#$5   jar名称，对应jenkins jarName

#/bin/cp -rf /home/jenkins/bigdataDeployScript/uploadFilesToSftpServer.sh .
#创建基础变量，方便ftp直接调用
#1.ftp目标文件夹下新建目录名称： 时间戳+应用名称
newFolder="$4_$3"
#2.重命名jar包名称


#$1类型意义
#1 只部署jar包
#2 只部署脚本文件
#3 同时部署jar和脚本文件
#null或其他，不执行任何操作	

if [ 1 == $1 ]
then 
	mv *-shaded.jar $5.jar
	jarFullName="$5.jar"
	echo "只上传jar包，不上传脚本文件夹"
	sftp -oIdentityFile=$secretDir  -oPort=$ftpPort  uploadwar@$ftpIp<<EOF
        #切换到ftp目标文件夹
        cd  $2
        #创建文件夹 时间戳-应用名称
        mkdir $newFolder
        cd $newFolder
        #上传jar包(jar包文件)
        put -r $jarFullName
EOF
elif [ 2 == $1 ]
then
	echo "只上传脚本文件夹，不上传jar包"
	sftp -oIdentityFile=$secretDir  -oPort=$ftpPort  uploadwar@$ftpIp <<EOF
        #切换到ftp目标文件夹
        cd  $2
        #创建文件夹 时间戳-应用名称
        mkdir $newFolder
        cd $newFolder
        #上传大数据脚本(文件夹)
        put -r $3/.
EOF
elif [ 3 == $1 ]
then
        mv *-shaded.jar $5.jar
        jarFullName="$5.jar"
	echo "同时上传jar包和脚本文件夹"
	sftp -oIdentityFile=$secretDir  -oPort=$ftpPort  uploadwar@$ftpIp <<EOF
	ls
	#切换到ftp目标文件夹
	cd  $2
	#创建文件夹 时间戳-应用名称
	mkdir $newFolder
	cd $newFolder
	#上传jar包(jar包文件)
	put -r $jarFullName
	#上传大数据脚本(文件夹)
	put -r $3/.
EOF
else 
	echo "不执行上传ftp操作!"
fi