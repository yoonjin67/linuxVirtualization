#!/bin/bash
NET_INTERFACE="$(ip route get 1 | awk '{print $5}')"
TAG="$1"
PORT="$2"
USERNAME="$3"
PASSWORD="$4"
VERSION="24.04"
SERVER_IP="$(ip route get 1 | awk '{print $7}')"
source /etc/environment
source /root/.bashrc
echo -n "TAG:"
echo $TAG
if [ $(arch)="x86_64" ]
then
		ARCH="amd64"
elif [ $(arch)="amd64" ]
then
		ARCH=$(arch)
else
		echo "Sorry, This architecture is not supported;" 1>&2
		echo "Supported architecture for Minecraft: amd64" 1>&2
		echo "Your architecture is $(arch)" 1>&2
		return
fi
incus launch images:ubuntu/$VERSION/$ARCH $TAG 


while true ; do 
	CONTAINER_IP=`incus list |  grep $TAG | awk '{print $7}' | grep --invert-match "|" | tr -s " " `
	LENGTH_IP=`echo $CONTAINER_IP | awk '{print length}'`
	if [  $LENGTH_IP = 0 ]; then
		sleep 0.5
	else 
		break
 fi
done
tail -n 1 /etc/nginx/nginx.conf | wc -c | xargs -I {} truncate /etc/nginx/nginx.conf -s -{}
echo "
	server {
		listen [::]:$((PORT+1));
		proxy_pass [$CONTAINER_IP]:30000;
	}
	server {
		listen [::]:$PORT;
		proxy_pass [$CONTAINER_IP]:3389;
	}
	server {
		listen [::]:$((PORT+2));
		proxy_pass [$CONTAINER_IP]:8080;
	}

}" >> /etc/nginx/nginx.conf

nginx -s reload
echo -n "CURRENT IP:"
echo $CONTAINER_IP
incus file push -r /usr/local/bin/linuxVirtualization/conSSH.sh $TAG/
incus exec $TAG -- /bin/apt-get update -y
incus exec $TAG -- /bin/apt-get install -y unzip openssh-server openssh-client sudo
incus exec $TAG -- useradd -m -s /bin/bash $USERNAME
incus exec $TAG -- sudo usermod -aG sudo "$USERNAME"
incus exec $TAG -- /bin/bash -c 'echo "$PASSWORD\n$PASSWORD" | passwd $USERNAME'
incus exec $TAG -- echo "$USERNAME ALL=(ALL:ALL) ALL" >> /etc/sudoers
echo $TAG > /usr/local/bin/linuxVirtualization/container/latest_access
incus exec $TAG -- /bin/apt-get install -y openssh-server sshpass
incus exec $TAG -- /bin/rm -rf /etc/ssh/sshd_config
incus exec $TAG -- /bin/systemctl restart --now ssh
incus exec $TAG -- /bin/bash /conSSH.sh $TAG
echo "LXC DEVICE STATUS:"
incus list
