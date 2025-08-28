


How to fill config.py:
go to imou life website, create a develloper account, create a new application and got AdminAccount, AppSecret, AppId 
the SECURITYCODE is under the camera
for the ip cmd prompt: arp -a
fill the config.py then run devicesNflux.py to get device ID and available flux then put them in config file
or get device ID from imou life app
the openapi base url may depend on you're region
https://open.imoulife.com/book/en/js/sdk.html?h=openapi:
      // For developers in Europe, please fill in https://openapi-fk.easy4ip.com; 
      // For developers in Asia, please fill in https://openapi-sg.easy4ip.com;
      // For developers in the Americas, please fill in https://openapi-or.easy4ip.com.
and for detection_device if you use and old graphic card, i recommand to use cpu instead of gpu

yolo models  : https://huggingface.co/Ultralytics/YOLOv8/tree/main
other models : https://github.com/anisayari/easy_facial_recognition/tree/master/pretrained_model


TODO:
face extraction from person_n
face recognition
check if audio work
enregistrement video/photo/audio
motion tracking



