
scp pi@10.6.17.46:/home/pi/.bashrc . ; opent .bashrc

alias long_exp='sudo -u pi crontab /home/pi/Tools/Crontab/LongExposure.txt; rm -rf /home/pi/Tools/Crontab/status/*; sudo -u pi touch /home/pi/Tools/Crontab/status/LongExposure; rm -rf /home/pi/Tools/Status/*; sudo -u pi touch /home/pi/Tools/Status/Ready'

scp .bashrc pi@10.6.17.46:/home/pi/.

scp 3s_config.txt pi@10.6.17.46:/home/pi/Tools/Camera/.

scp LongExposure.txt pi@10.6.17.46:/home/pi/Tools/Crontab/.

scp index.php pi@10.6.17.46:/home/pi/Tools/Web/camera/.

10.6.17.46
10.6.18.243

scp light_switchon_config.txt pi@10.6.17.171:/home/pi/Tools/Camera/.
scp battery_config.txt pi@10.6.17.171:/home/pi/Tools/Camera/.

scp Battery.txt pi@10.6.17.171:/home/pi/Tools/Crontab/.

python3 /home/pi/Tools/Camera/gonet4.py /home/pi/Tools/Camera/light_switchon_config.txt
sudo -u pi crontab /home/pi/Tools/Crontab/Dark.txt; rm -rf /home/pi/Tools/Crontab/status/*; sudo -u pi touch /home/pi/Tools/Crontab/status/Battery; rm -rf /home/pi/Tools/Status/*; sudo -u pi touch /home/pi/Tools/Status/Ready