from binance.client import Client
from datetime import datetime
import time
import telegram
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
from threading import Thread
import os
import configparser


#v1 : 가격 확인후 거래만
#v2 : 텔레그램 봇을 통해 현재 상황 및 메세지 확인, 평균 진입금액에서 -3%일때 추가구매
#v3 : 평균 최근 구매액에서 -3%일때 추가구매

def config_read():
    config = configparser.ConfigParser()    
    config.read('config.ini', encoding='utf-8') 

    api_key = config['Binance']['api_key']
    api_secret  = config['Binance']['api_secret']
    token = config['Telegram']['token']
    chat_id = config['Telegram']['chat_id']
    return api_key, api_secret, token, chat_id

def check_balance(account):
    for bl in account['assets']:
        if bl['asset'] == 'USDT':
            total_balance = round(float(bl['walletBalance']),3)
            avail_balance = round(float(bl['availableBalance']),3)
            initialmargin = float(bl['initialMargin'])
            unrealizedprofit = float(bl['unrealizedProfit'])
            if unrealizedprofit != 0:
                pnl = unrealizedprofit
                roe = round(unrealizedprofit / initialmargin*100,3)
            else:
                pnl = 0
                roe = 0

    return total_balance, avail_balance, initialmargin, pnl, roe

def check_position(account):
    active_position = []    
    for position in account['positions']:
        if position['symbol'] == 'BTCUSDT':
            active_position.append(position)
    return active_position

def buy_coin(symbol, quantity):
    order = client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=quantity)   
    return order

def added_buy_coin(symbol, quantity, price):
    order = client.futures_create_order(symbol=symbol, side='BUY', type='LIMIT', timeInForce='GTC', quantity=quantity, price=price)
    return order

def close_postion(symbol, quantity):
    print(quantity)
    order = client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=quantity)
    return order


def main_transaction():
    while(1):
        #configuration
        initamount = 10 # 10$
        next_amount = 0 #초기화만 하고 구매할때마다 계산
        
        try:
            #balance = client.futures_account_balance()
            account = client.futures_account()
        
            # Step1. 현재 잔액 및 수익률 확인
            total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
            print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')

            # Step2. 현재 포지션 확인
            active_position = check_position(account)

            #포지션이 있는경우
            if active_position[0]['isolatedWallet'] != '0':
                print("[i]기존 포지션이 있습니다! 포지션 총 구매금액($) : " + str(active_position[0]['isolatedWallet']) +', 포지션 평균 진입 금액 : '+ str(active_position[0]['entryPrice']))
                # Step4. 포지션 종료가 설정
                target_sell_price = int(float(active_position[0]['entryPrice']) * sell_rate)
                print("[i]포지션 종료가 설정("+str(sell_rate)+") : "+str(target_sell_price))
                # step5. 추가 구매가 설정
                tartget_buy_price = int(float(active_position[0]['entryPrice']) * buy_rate)
                print("[i]추가 구매가 설정("+str(buy_rate)+") : "+str(tartget_buy_price))
                # step6. 추가 구매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                next_amount = int((float(active_position[0]['isolatedWallet']) * 1.1 + initamount))
                print("[i]추가 구매액 재설정($, 현재 포지션 총 구매금액 + 초기금액(약 2배씩 구매)) : "+str(next_amount))
            
            #포지션이 없는 경우
            else:
                print("현재 포지션이 없습니다. 포지션 오픈 하겠습니다. ")
                # Step3. 최초 구매(포지션 오픈)
                current_price = client.futures_symbol_ticker(symbol="BTCUSDT")
                quantity = round(float(initamount)/float(current_price['price'])*10,3)
                order = buy_coin(symbol, quantity)
                time.sleep(5)
                account = client.futures_account()
                active_position = check_position(account)
                msg1 = "[+]포지션 오픈 성공 : "+str(order['orderId'])+"\n포지션 총 구매금액($) : " + str(active_position[0]['isolatedWallet']) +'\n포지션 평균 진입 금액 : '+ str(active_position[0]['entryPrice'])
                print(msg1)
                #bot.send_message(chat_id = chat_id, text=msg1, disable_notification=False)  
                
                # Step4. 포지션 종료가 설정
                target_sell_price = int(float(active_position[0]['entryPrice']) * sell_rate)
                print("[i]포지션 종료가 설정("+str(sell_rate)+") : "+str(target_sell_price))
                # step5. 추가 구매가 설정
                tartget_buy_price = int(float(active_position[0]['entryPrice']) * buy_rate)
                print("[i]추가 구매가 설정("+str(buy_rate)+") : "+str(tartget_buy_price))
                # step6. 추가 구매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                next_amount = int((float(active_position[0]['isolatedWallet']) * 1.1 + initamount))
                print("[i]추가 구매액 재설정($, 현재 포지션 총 구매금액 + 초기금액(약 2배씩 구매)) : "+str(next_amount))
                # 잔액 등 확인
                total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')

            price_print_cnt = 0
            while(1):
                #5초에 한번 BTC 가격 확인
                current_price = client.futures_symbol_ticker(symbol="BTCUSDT")
                if price_print_cnt == 0:
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 BTC 가격 : ' + str(current_price['price'])+ ', 현재 포지션 양 : '+ str(active_position[0]['positionAmt']) + ', 포지션 종료가 : '+ str(target_sell_price)+', 추가 구매가 : ' +str(tartget_buy_price))
                    price_print_cnt = price_print_cnt + 1
                elif price_print_cnt > 50:
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 BTC 가격 : ' + str(current_price['price'])+ ', 현재 포지션 양 : '+ str(active_position[0]['positionAmt']) + ', 포지션 종료가 : '+ str(target_sell_price)+', 추가 구매가 : ' +str(tartget_buy_price))
                    price_print_cnt = 1
                else:
                    price_print_cnt = price_print_cnt + 1
                    pass
                #Step7. 추가 구매
                if (float(current_price['price']) < float(tartget_buy_price)):
                    now = datetime.now()
                    print("[d] "+str(int(avail_balance))+", "+str(int(next_amount)))
                    if avail_balance >= next_amount:
                        quantity = round(float(next_amount)/float(current_price['price'])*10,3)
                        order = buy_coin(symbol, quantity)
                        time.sleep(5)
                        account = client.futures_account()
                        active_position = check_position(account)
                        msg2 = "[+]추가 구매 성공 : "+str(order['orderId'])+"\n포지션 총 구매금액($) : " + str(active_position[0]['isolatedWallet']) +'\n포지션 평균 진입 금액 : '+ str(active_position[0]['entryPrice'])
                        print(msg2)
                        #bot.send_message(chat_id = chat_id, text=msg2, disable_notification=False)

                        #Step7. 포지션 종료가 및 추가 구매가 재설정
                        target_sell_price = int(float(active_position[0]['entryPrice']) * sell_rate)
                        print("[i]포지션 종료가 재설정("+str(sell_rate)+") : "+str(target_sell_price))
                        tartget_buy_price = int(float(active_position[0]['entryPrice']) * buy_rate)
                        print("[i]추가 구매가 재설정("+str(buy_rate)+") : "+str(tartget_buy_price))
                        next_amount = int((float(active_position[0]['isolatedWallet']) * 1.1 + initamount))
                        print("[i]추가 구매액 재설정($, 현재 포지션 총 구매금액 + 초기금액(약 2배씩 구매)) : "+str(next_amount))
                        # 잔액 등 확인
                        total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                        print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')
                    else:
                        print("[-] 구매금액이 부족하여 추가 구매 실패.. 가용 자산 : "+str(avail_balance)+"$, 추가 구매액 : "+str(next_amount))

                #Step8. 포지션 종료
                elif (float(current_price['price']) > float(target_sell_price)):
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 BTC 가격 : ' + str(current_price['price'])+ ', 현재 포지션 양 : '+ str(active_position[0]['positionAmt']) + ', 포지션 종료가 : '+ str(target_sell_price)+', 추가 구매가 : ' +str(tartget_buy_price))
                    order = close_postion(symbol, active_position[0]['positionAmt'])
                    time.sleep(5)
                    msg3 = "[+]포지션 종료 성공 : "+str(order['orderId'])+"\n포지션 총 판매금액($) : " + str(active_position[0]['isolatedWallet']) +'\n포지션 예상 수익 : '+ str(round((float(current_price['price']) - float(active_position[0]['entryPrice'])) * float(active_position[0]['positionAmt']),2))
                    print(msg3)
                    #bot.send_message(chat_id = chat_id, text=msg3, disable_notification=False)
                    break
                else:
                    pass

                time.sleep(5)
        except Exception as e:
            print("[-]Critical Error")
            print(e.message)
            os._exit(1)
            #continue



##################################Telegram Bot##################################
def check_status(update: Update, _: CallbackContext) -> None:
    current_price = client.futures_symbol_ticker(symbol="BTCUSDT")
    account = client.futures_account()
    active_position = check_position(account)    
    total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
    target_sell_price = int(float(active_position[0]['entryPrice']) * sell_rate)
    tartget_buy_price = int(float(active_position[0]['entryPrice']) * buy_rate)

    now = datetime.now()
    msg = '['+now.strftime('%Y-%m-%d %H:%M:%S')+']\n현재 BTC 가격 : '+ str(current_price['price'])+ '$' +\
            '\n현재 포지션 양 : '+ str(active_position[0]['positionAmt']) + 'btc' +\
                '\n포지션 종료가 : '+ str(target_sell_price)+ '$' +\
                    '\n추가 구매가 : ' +str(tartget_buy_price)+ '$' + \
                        '\n######balance######'+ \
                        '\n총 자산(거래전) : '+ str(total_balance)+ '$' + \
                            '\n가용 자산 : '+str(avail_balance)+ '$' + \
                                '\n마진 금액(수익포함) : '+str(round(initialmargin, 3))+ '$' + \
                                    '\n포지션 평균 진입 금액 : '+ str(round(float(active_position[0]['entryPrice']),1)) + '$' +\
                                        '\nPNL : '+str(round(pnl,2))+ '$' + \
                                            '\nROE : '+str(roe)+ '%'

    bot.send_message(chat_id = chat_id, text=msg, disable_notification=False)    

def quit(update: Update, _: CallbackContext) -> None:
    bot.send_message(chat_id = chat_id, text="봇을 종료합니다", disable_notification=False)    
    os._exit(1)

def commander() -> None:
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("status", check_status))
    dispatcher.add_handler(CommandHandler("quit", quit))
    updater.start_polling()

def main():
    #실시간 가격 확인 및 거래 모듈
    p1 = Thread(target = main_transaction)
    #텔레그램봇
    p2 = Thread(target = commander)

    p1.start()
    p2.start()

if __name__ == '__main__':
    api_key, api_secret, token, chat_id = config_read()
    #telegram
    bot = telegram.Bot(token=token)
    #binance
    api_key = api_key
    api_secret = api_secret
    client = Client(api_key = api_key, api_secret=api_secret, testnet = False)
    #평균 구매가 기준
    sell_rate = 1.02
    buy_rate = 0.97
    symbol = 'BTCUSDT'
    #start
    main()
