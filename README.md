# 바이낸스 선물 자동 매매 프로그램
> 물타기 전략을 통한 바이낸스 선물 자동 매매 프로그램입니다.

## Binance_Futures_Bot 준비물
1. 바이낸스 API
 
      1.1. Binance API Management에서 API 생성할때 Enable Reading, Enable Futures만 체크하고, 보안상 AWS 서버 구축후에 서버의 IP를 허용 IP에 넣어주면됨
 
2. Telegram Token, Chat ID

      2.1. Token : Telegram 설치후 @botfather 검색, /newbot이라고 치면 봇생성을 위한 이름 등을 입력하라고 나옴. 모두 설정하면 token API가 숫자:영어숫자 형식으로 나옴
      
      2.2. Chat ID : @userinfobot 검색, 시작 누르면 id가 숫자로 나오는데 이것이 chat id


3. AWS 서버

      3.1. AWS 생성 : 아마존 aws 가입 후 lightsail 서비스에서 Create Instance를 누르고, Linux - OS Only - Ubuntu 20.04, 5$요금제 선택

      3.2. Linux 서버 설정
            
       1. 한글패치(이거안하면 한글깨짐) : sudo locale-gen ko_KR.UTF-8 
       2. pip 설치
         2.1. sudo apt update
         2.2. sudo apt upgrade
         2.3. sudo apt install python3-pip
       3. 소스코드 다운로드
         3.1. git clone https://github.com/HomeMakerMan/Binance_Futures_Bot


## Binance_Futures_Bot 실행방법
1. config.ini에 들어가서 binance api 정보와 Telegram token, chat id 정보를 입력 후 저장
2. 실행 쉘 파일에 실행권한을 부여
```sh
chmod 764 startup.sh
chmod 764 shutdown.sh
```
3. 봇 실행
```sh
./startup.sh
```
4. 봇이 잘 돌고있는지 확인방법
```sh
ps -ef | grep python3
또는, Telegram에서 본인이 만든 봇에서 /status를 치면 현재 포지션등이 나옴
```

## 기타사항

바이낸스 선물거래는 매매시 핸드폰에 알람이 안옴, 그래서 telegram을 연동 시켰으나, telegram 서버가 불안정해서인지 가끔 에러가 나는 경우가 있음. 그래서 매매시 보내지는 메시지는 주석처리 했음. 코드를 수정해도 되지만, 처음에만 바이낸스에 자주들어가서 프로그램이 잘 돌고있는지만 확인해보면되고, 그 이후에는 신경쓰기 싫으니 차라리 아무것도 안오고 안보는게 더 좋음


## 정보

Youtube : 주부가 되고싶은 남편(https://www.youtube.com/channel/UC5pWKVG5Hsob-SW112QmfjQ)
