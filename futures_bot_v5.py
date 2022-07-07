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
    config.read('config_v5.ini', encoding='utf-8') 

    api_key = config['Binance']['api_key']
    api_secret  = config['Binance']['api_secret']
    BTC_sell_rate = float(config['Rate']['BTC_sell_rate'])
    BTC_buy_rate = float(config['Rate']['BTC_buy_rate'])
    ETH_sell_rate = float(config['Rate']['ETH_sell_rate'])
    ETH_buy_rate = float(config['Rate']['ETH_buy_rate'])

    return api_key, api_secret, BTC_sell_rate, BTC_buy_rate, ETH_sell_rate, ETH_buy_rate

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
    for position in account['positions']:
        if position['symbol'] == 'BTCUSDT':
            position_BTC = position
        elif position['symbol'] == 'ETHUSDT':
            position_ETH = position
        else:
            pass
    return position_BTC, position_ETH

def buy_coin(symbol, quantity):
    order = client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=quantity)   
    return order

def added_buy_coin(symbol, quantity, price):
    order = client.futures_create_order(symbol=symbol, side='BUY', type='LIMIT', timeInForce='GTC', quantity=quantity, price=price)
    return order

def sell_coin(symbol, quantity):
    print(quantity)
    order = client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=quantity)
    return order


def main_transaction():
    while(1):
        #configuration
        initamount = 10 # 10$
        
        try:
            #balance = client.futures_account_balance()
            account = client.futures_account()
        
            # Step1. 현재 잔액 및 수익률 확인
            total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
            print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')

            # Step2. 현재 포지션 확인
            position_BTC, position_ETH = check_position(account)
            
            
            #포지션이 있는경우
            if position_BTC['isolatedWallet'] != '0':
                print("####### BTC(Long) #######")
                print("[i]기존 포지션이 있습니다! 포지션 총 구매금액($) : " + str(position_BTC['isolatedWallet']) +', 포지션 평균 진입 금액 : '+ str(position_BTC['entryPrice']))
                # Step4. 포지션 종료가 설정
                BTC_target_sell_price = int(float(position_BTC['entryPrice']) * BTC_sell_rate)
                print("[i]포지션 종료가 설정("+str(BTC_sell_rate)+") : "+str(BTC_target_sell_price))
                # step5. 추가 구매가 설정
                BTC_tartget_buy_price = int(float(position_BTC['entryPrice']) * BTC_buy_rate)
                print("[i]추가 구매가 설정("+str(BTC_buy_rate)+") : "+str(BTC_tartget_buy_price))
                # step6. 추가 구매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) + 최초 구매금액)
                BTC_next_amount = int((float(position_BTC['isolatedWallet']) * 1.1 + initamount))
                print("[i]추가 구매액 재설정($, 현재 포지션 총 구매금액 + 초기금액(약 2배씩 구매)) : "+str(BTC_next_amount))
            
            if position_ETH['isolatedWallet'] != '0':
                print("####### ETH(Short) #######")
                print("[i]기존 포지션이 있습니다! 포지션 총 구매금액($) : " + str(position_ETH['isolatedWallet']) +', 포지션 평균 진입 금액 : '+ str(position_ETH['entryPrice']))
                # Step4. 포지션 종료가 설정
                ETH_tartget_buy_price = int(float(position_ETH['entryPrice']) * ETH_buy_rate)
                print("[i]포지션 종료가 설정("+str(ETH_buy_rate)+") : "+str(ETH_tartget_buy_price))
                # step5. 추가 판매가 설정
                ETH_target_sell_price = int(float(position_ETH['entryPrice']) * ETH_sell_rate)
                print("[i]추가 판매가 설정("+str(ETH_sell_rate)+") : "+str(ETH_target_sell_price))
                # step6. 추가 판매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                ETH_next_amount = int((float(position_ETH['isolatedWallet']) * 1.1 + initamount))
                print("[i]추가 판매액 재설정($, 현재 포지션 총 판매금액 + 초기금액(약 2배씩 구매)) : "+str(ETH_next_amount))


            #포지션이 없는 경우
            if position_BTC['isolatedWallet'] == '0':
                print("####### BTC(Long) #######")
                print("현재 포지션이 없습니다. 포지션 오픈 하겠습니다. ")
                # Step3. 최초 구매(포지션 오픈)
                symbol = "BTCUSDT"
                current_price = client.futures_symbol_ticker(symbol=symbol)
                quantity = round(float(initamount)/float(current_price['price'])*10,3)
                order = buy_coin(symbol, quantity)
                time.sleep(5)
                account = client.futures_account()
                position_BTC, position_ETH = check_position(account)

                msg1 = "[+]포지션 오픈 성공 : "+str(order['orderId'])+"\n포지션 총 구매금액($) : " + str(position_BTC['isolatedWallet']) +'\n포지션 평균 진입 금액 : '+ str(position_BTC['entryPrice'])
                print(msg1)
                
                # Step4. 포지션 종료가 설정
                BTC_target_sell_price = int(float(position_BTC['entryPrice']) * BTC_sell_rate)
                print("[i]포지션 종료가 설정("+str(BTC_sell_rate)+") : "+str(BTC_target_sell_price))
                # step5. 추가 구매가 설정
                BTC_tartget_buy_price = int(float(position_BTC['entryPrice']) * BTC_buy_rate)
                print("[i]추가 구매가 설정("+str(BTC_buy_rate)+") : "+str(BTC_tartget_buy_price))
                # step6. 추가 구매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                BTC_next_amount = int((float(position_BTC['isolatedWallet']) * 1.1 + initamount))
                print("[i]추가 구매액 재설정($, 현재 포지션 총 구매금액 + 초기금액(약 2배씩 구매)) : "+str(BTC_next_amount))
                # 잔액 등 확인
                total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')

            if position_ETH['isolatedWallet'] == '0':
                print("####### ETH(Short) #######")
                print("현재 포지션이 없습니다. 포지션 오픈 하겠습니다. ")
                # Step3. 최초 구매(포지션 오픈)
                symbol = "ETHUSDT"
                current_price = client.futures_symbol_ticker(symbol=symbol)
                quantity = round(float(initamount)/float(current_price['price'])*10,3)
                order = sell_coin(symbol, quantity)
                time.sleep(5)
                account = client.futures_account()
                position_BTC, position_ETH = check_position(account)

                msg1 = "[+]포지션 오픈 성공 : "+str(order['orderId'])+"\n포지션 총 구매금액($) : " + str(position_ETH['isolatedWallet']) +'\n포지션 평균 진입 금액 : '+ str(position_ETH['entryPrice'])
                print(msg1)

                # Step4. 포지션 종료가 설정
                ETH_tartget_buy_price = int(float(position_ETH['entryPrice']) * ETH_buy_rate)
                print("[i]포지션 종료가 설정("+str(ETH_buy_rate)+") : "+str(ETH_tartget_buy_price))
                # step5. 추가 판매가 설정
                ETH_target_sell_price = int(float(position_ETH['entryPrice']) * ETH_sell_rate)
                print("[i]추가 판매가 설정("+str(ETH_sell_rate)+") : "+str(ETH_target_sell_price))
                # step6. 추가 판매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                ETH_next_amount = int((float(position_ETH['isolatedWallet']) * 1.1 + initamount))
                print("[i]추가 판매액 재설정($, 현재 포지션 총 판매금액 + 초기금액(약 2배씩 구매)) : "+str(ETH_next_amount))

                # 잔액 등 확인
                total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')



            price_print_cnt = 0
            while(1):
                #5초에 한번 BTC 가격 확인
                BTC_current_price = client.futures_symbol_ticker(symbol="BTCUSDT")
                ETH_current_price = client.futures_symbol_ticker(symbol="ETHUSDT") 
                
                if price_print_cnt == 0:
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 BTC 가격 : ' + str(BTC_current_price['price'])+ ', 현재 포지션 양 : '+ str(position_BTC['positionAmt']) + ', 포지션 종료가 : '+ str(BTC_target_sell_price)+', 추가 구매가 : ' +str(BTC_tartget_buy_price))
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 ETH 가격 : ' + str(ETH_current_price['price'])+ ', 현재 포지션 양 : '+ str(position_ETH['positionAmt']) + ', 포지션 종료가 : '+ str(ETH_tartget_buy_price)+', 추가 판매가 : ' +str(ETH_target_sell_price))
                    price_print_cnt = price_print_cnt + 1
                elif price_print_cnt > 50:
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 BTC 가격 : ' + str(BTC_current_price['price'])+ ', 현재 포지션 양 : '+ str(position_BTC['positionAmt']) + ', 포지션 종료가 : '+ str(BTC_target_sell_price)+', 추가 구매가 : ' +str(BTC_tartget_buy_price))
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 ETH 가격 : ' + str(ETH_current_price['price'])+ ', 현재 포지션 양 : '+ str(position_ETH['positionAmt']) + ', 포지션 종료가 : '+ str(ETH_tartget_buy_price)+', 추가 판매가 : ' +str(ETH_target_sell_price))
                    price_print_cnt = 1
                else:
                    price_print_cnt = price_print_cnt + 1
                    pass


                #Step7. BTC(LONG) 추가 구매
                if (float(BTC_current_price['price']) < float(BTC_tartget_buy_price)):
                    symbol = "BTCUSDT"
                    now = datetime.now()
                    print("[d] "+str(int(avail_balance))+", "+str(int(BTC_next_amount)))
                    if avail_balance >= BTC_next_amount:
                        quantity = round(float(BTC_next_amount)/float(BTC_current_price['price'])*10,3)
                        order = buy_coin(symbol, quantity)
                        time.sleep(5)
                        account = client.futures_account()
                        position_BTC, position_ETH = check_position(account)
                        msg2 = "[+][BTC(Long)]추가 구매 성공 : "+str(order['orderId'])+"\n포지션 총 구매금액($) : " + str(position_BTC['isolatedWallet']) +'\n포지션 평균 진입 금액 : '+ str(position_BTC['entryPrice'])
                        print(msg2)

                        #Step7. 포지션 종료가 및 추가 구매가 재설정
                        BTC_target_sell_price = int(float(position_BTC['entryPrice']) * BTC_sell_rate)
                        print("[i][BTC(Long)]포지션 종료가 재설정("+str(BTC_sell_rate)+") : "+str(BTC_target_sell_price))
                        BTC_tartget_buy_price = int(float(position_BTC['entryPrice']) * BTC_buy_rate)
                        print("[i][BTC(Long)]추가 구매가 재설정("+str(BTC_buy_rate)+") : "+str(BTC_tartget_buy_price))
                        BTC_next_amount = int((float(position_BTC['isolatedWallet']) * 1.1 + initamount))
                        print("[i][BTC(Long)]추가 구매액 재설정($, 현재 포지션 총 구매금액 + 초기금액(약 2배씩 구매)) : "+str(BTC_next_amount))
                        # 잔액 등 확인
                        total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                        print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')
                    else:
                        print("[-] 구매금액이 부족하여 추가 구매 실패.. 가용 자산 : "+str(avail_balance)+"$, 추가 구매액 : "+str(BTC_next_amount))

                #Step8.  BTC(LONG) 포지션 종료
                elif (float(BTC_current_price['price']) > float(BTC_target_sell_price)):
                    symbol = "BTCUSDT"
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 BTC 가격 : ' + str(BTC_current_price['price'])+ ', 현재 포지션 양 : '+ str(position_BTC['positionAmt']) + ', 포지션 종료가 : '+ str(BTC_target_sell_price)+', 추가 구매가 : ' +str(BTC_tartget_buy_price))
                    order = sell_coin(symbol, position_BTC['positionAmt'])
                    time.sleep(5)
                    msg3 = "[+][BTC(Long)]포지션 종료 성공 : "+str(order['orderId'])+"\n포지션 총 판매금액($) : " + str(position_BTC['isolatedWallet']) +'\n포지션 예상 수익 : '+ str(round((float(BTC_current_price['price']) - float(position_BTC['entryPrice'])) * float(position_BTC['positionAmt']),2))
                    print(msg3)
                    break
                else:
                    pass



                #Step7. ETH(Short) 추가 판매
                if (float(ETH_current_price['price']) > float(ETH_target_sell_price)):
                    symbol = "ETHUSDT"
                    now = datetime.now()
                    print("[d] "+str(int(avail_balance))+", "+str(int(ETH_next_amount)))
                    if avail_balance >= ETH_next_amount:
                        quantity = round(float(ETH_next_amount)/float(ETH_current_price['price'])*10,3)
                        order = sell_coin(symbol, quantity)
                        time.sleep(5)
                        account = client.futures_account()
                        position_BTC, position_ETH = check_position(account)
                        msg2 = "[+][ETH(Short)]추가 판매 성공 : "+str(order['orderId'])+"\n포지션 총 구매금액($) : " + str(position_ETH['isolatedWallet']) +'\n포지션 평균 진입 금액 : '+ str(position_ETH['entryPrice'])
                        print(msg2)
                        #bot.send_message(chat_id = chat_id, text=msg2, disable_notification=False)

                        #Step7. 포지션 종료가 및 추가 구매가 재설정
                        ETH_tartget_buy_price = int(float(position_ETH['entryPrice']) * ETH_buy_rate)
                        print("[i][ETH(Short)]포지션 종료가 설정("+str(ETH_buy_rate)+") : "+str(ETH_tartget_buy_price))
                        ETH_target_sell_price = int(float(position_ETH['entryPrice']) * ETH_sell_rate)
                        print("[i][ETH(Short)]추가 판매가 설정("+str(ETH_sell_rate)+") : "+str(ETH_target_sell_price))
                        ETH_next_amount = int((float(position_ETH['isolatedWallet']) * 1.1 + initamount))
                        print("[i][ETH(Short)]추가 판매액 재설정($, 현재 포지션 총 구매금액 + 초기금액(약 2배씩 구매)) : "+str(ETH_next_amount))

                        # 잔액 등 확인
                        total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                        print('[i]총 자산(거래전) : '+ str(total_balance)+'$, 가용 자산 : '+str(avail_balance)+'$, 마진 금액(수익포함) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')
                        #os._exit(1)
                    else:
                        print("[-] 구매금액이 부족하여 추가 판매 실패.. 가용 자산 : "+str(avail_balance)+"$, 추가 판매액 : "+str(ETH_next_amount))

                #Step8.  ETH(Short) 포지션 종료
                elif (float(ETH_current_price['price']) < float(ETH_tartget_buy_price)):
                    symbol = "ETHUSDT"
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']현재 ETH 가격 : ' + str(ETH_current_price['price'])+ ', 현재 포지션 양 : '+ str(position_ETH['positionAmt']) + ', 포지션 종료가 : '+ str(ETH_tartget_buy_price)+', 추가 판매가 : ' +str(ETH_target_sell_price))
                    order = buy_coin(symbol, abs(float(position_ETH['positionAmt'])))
                    time.sleep(5)
                    msg3 = "[+][ETH(Short)]포지션 종료 성공 : "+str(order['orderId'])+"\n포지션 총 판매금액($) : " + str(position_ETH['isolatedWallet']) +'\n포지션 예상 수익 : '+ str(round((float(ETH_current_price['price']) - float(position_ETH['entryPrice'])) * float(position_ETH['positionAmt']),2))
                    print(msg3)
                    #os._exit(1)
                    break
                else:
                    pass

                time.sleep(5)
        except:
            print('[-]Error Restart')
            time.sleep(60)
            #os._exit(1)
            continue



def main():
    #실시간 가격 확인 및 거래 모듈
    main_transaction()

if __name__ == '__main__':
    api_key, api_secret, BTC_sell_rate, BTC_buy_rate, ETH_sell_rate, ETH_buy_rate = config_read()
    #binance
    api_key = api_key
    api_secret = api_secret
    client = Client(api_key = api_key, api_secret=api_secret, testnet = False)

    main()
