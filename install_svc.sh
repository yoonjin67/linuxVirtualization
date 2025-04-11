if [ $(whoami) = "root" ]
then
    cp -r linuxVirtualization.service /usr/lib/systemd/system/linuxVirtualization.service
    cd ..
    rm -r /usr/local/bin/linuxVirtualization
    rm -r /usr/local/bin/apply_nginx.sh
    rm -r /usr/local/bin/clean.sh
    rm -r /usr/local/bin/conSSH.sh
    rm -r /usr/local/bin/easy_access.sh
    rm -r /usr/local/bin/remove-service.sh
    rm -r /usr/local/bin/initial_setup.sh
    rm -r /usr/local/bin/install_svc.sh
    rm -r /usr/local/bin/killall.sh
    rm -r /usr/local/bin/kill.sh
    rm -r /usr/local/bin/server.sh
    rm -r '/usr/local/bin/*.sh'
    rm -r /usr/local/bin/server
    echo  "Copying files..."
    mkdir /usr/local/bin/linuxVirtualization
    cp -Rf linuxVirtualization/* /usr/local/bin/linuxVirtualization
    ln -s /usr/local/bin/linuxVirtualization/*.sh /usr/local/bin
    ln -s /usr/local/bin/linuxVirtualization/linuxVirtualiztionServer /usr/local/bin
    systemctl daemon-reload
    systemctl enable --now linuxVirtualization
    systemctl start  --now linuxVirtualization
    echo "Done"
else
    sudo -s
fi
