from binance.client import Client
from datetime import datetime
import time
import configparser

#config_v6.ini 파일에 바이낸스 api key, secret key, 리플 매도 비율, 리플 매수 비율, 비트코인 매도 비율, 비트코인 매수 비율 입력
#설정 파일 로드
def config_read():
    config = configparser.ConfigParser()    
    config.read('config_v6.ini', encoding='utf-8') 

    
    api_key = config['Binance']['api_key']
    api_secret  = config['Binance']['api_secret']
    XRP_sell_rate = float(config['Rate']['XRP_sell_rate'])
    XRP_buy_rate = float(config['Rate']['XRP_buy_rate'])
    BTC_sell_rate = float(config['Rate']['BTC_sell_rate'])
    BTC_buy_rate = float(config['Rate']['BTC_buy_rate'])

    return api_key, api_secret, XRP_sell_rate, XRP_buy_rate, BTC_sell_rate, BTC_buy_rate

#현재 잔고 확인
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

#현재 포지션 확인
def check_position(account):
    for position in account['positions']:
        if position['symbol'] == 'XRPUSDT':
            position_XRP = position
        elif position['symbol'] == 'BTCUSDT':
            position_BTC = position
        else:
            pass
    return position_XRP, position_BTC

#코인 매수
def buy_coin(symbol, quantity):
    order = client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=quantity)   
    return order

#코인 추가 매수
def added_buy_coin(symbol, quantity, price):
    order = client.futures_create_order(symbol=symbol, side='BUY', type='LIMIT', timeInForce='GTC', quantity=quantity, price=price)
    return order

#코인 매도
def sell_coin(symbol, quantity):
    print(quantity)
    order = client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=quantity)
    return order

#핵심 코드
def main_transaction():
    while(1):
        #configuration
        #초기비용 10$ 설정
        initamount = 10
        
        try:
            account = client.futures_account()
        
            # Step1. 현재 잔액 및 수익률 확인
            total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
            print('[i]Total Asset(before start) : '+ str(total_balance)+'$, Available Asset : '+str(avail_balance)+'$, Margin Asset(Included Profit) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')

            # Step2. 현재 포지션 확인
            position_XRP, position_BTC = check_position(account)
            
            #포지션이 있는경우(리플 : 가격이 떨어지면 더사고, 오르면 팔고)
            if position_XRP['isolatedWallet'] != '0':
                print("####### XRP(Long) #######")
                print("[i]Exists Position! Position total amount($) : " + str(position_XRP['isolatedWallet']) +', entryprice of position : '+ str(position_XRP['entryPrice']))
                # Step4. 포지션 종료가 설정
                XRP_target_sell_price = float(position_XRP['entryPrice']) * XRP_sell_rate
                print("[i]Set close price of position("+str(XRP_sell_rate)+") : "+str(XRP_target_sell_price))
                # step5. 추가 구매가 설정
                XRP_tartget_buy_price = float(position_XRP['entryPrice']) * XRP_buy_rate
                print("[i]Set add price("+str(XRP_buy_rate)+") : "+str(XRP_tartget_buy_price))
                # step6. 추가 구매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) + 최초 구매금액)
                XRP_next_amount = (float(position_XRP['isolatedWallet']) * 1.05 + initamount)
                print("[i]Reset add amount of position($, amount of current position + inital price(about x 2)) : "+str(XRP_next_amount))
            
            #포지션이 있는경우(비트코인 : 가격이 떨어지면 팔고, 오르면 더사고)
            if position_BTC['isolatedWallet'] != '0':
                print("####### BTC(Short) #######")
                print("[i]Exists Position! Position total amount($) : " + str(position_BTC['isolatedWallet']) +', entryprice of position : '+ str(position_BTC['entryPrice']))
                # Step4. 포지션 종료가 설정
                BTC_tartget_buy_price = int(float(position_BTC['entryPrice']) * BTC_buy_rate)
                print("[i]Set close price of position("+str(BTC_buy_rate)+") : "+str(BTC_tartget_buy_price))
                # step5. 추가 판매가 설정
                BTC_target_sell_price = int(float(position_BTC['entryPrice']) * BTC_sell_rate)
                print("[i]Set add price("+str(BTC_sell_rate)+") : "+str(BTC_target_sell_price))
                # step6. 추가 판매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                BTC_next_amount = int((float(position_BTC['isolatedWallet']) * 1.05 + initamount))
                print("[i]Reset add amount of position($, amount of current position + inital price(about x 2)) : "+str(BTC_next_amount))


            #포지션이 없는 경우(리플)
            if position_XRP['isolatedWallet'] == '0':
                print("####### XRP(Long) #######")
                print("No position, open new position.")
                # Step3. 최초 구매(포지션 오픈)
                symbol = "XRPUSDT"
                current_price = client.futures_symbol_ticker(symbol=symbol)
                quantity = int(float(initamount)/float(current_price['price'])*7)
                order = buy_coin(symbol, quantity)
                time.sleep(5)
                account = client.futures_account()
                position_XRP, position_BTC = check_position(account)

                msg1 = "[+]Success new position open : "+str(order['orderId'])+"\nPosition total amount($) : " + str(position_XRP['isolatedWallet']) +'\nentryprice of position : '+ str(position_XRP['entryPrice'])
                print(msg1)
                
                # Step4. 포지션 종료가 설정
                XRP_target_sell_price = float(position_XRP['entryPrice']) * XRP_sell_rate
                print("[i]Set close price of position("+str(XRP_sell_rate)+") : "+str(XRP_target_sell_price))
                # step5. 추가 구매가 설정
                XRP_tartget_buy_price = float(position_XRP['entryPrice']) * XRP_buy_rate
                print("[i]Set add price("+str(XRP_buy_rate)+") : "+str(XRP_tartget_buy_price))
                # step6. 추가 구매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                XRP_next_amount = (float(position_XRP['isolatedWallet']) * 1.05 + initamount)
                print("[i][i]Reset add amount of position($, amount of current position + inital price(about x 2)) : "+str(XRP_next_amount))
                # 잔액 등 확인
                total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                print('[i]Total Asset(before start) : '+ str(total_balance)+'$, Available Asset : '+str(avail_balance)+'$, Margin Asset(Included Profit) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')

            #포지션이 없는 경우(비트코인)
            if position_BTC['isolatedWallet'] == '0':
                print("####### BTC(Short) #######")
                print("No position, open new position. ")
                # Step3. 최초 구매(포지션 오픈)
                symbol = "BTCUSDT"
                current_price = client.futures_symbol_ticker(symbol=symbol)
                quantity = round(float(initamount)/float(current_price['price'])*7,3)
                order = sell_coin(symbol, quantity)
                time.sleep(5)
                account = client.futures_account()
                position_XRP, position_BTC = check_position(account)

                msg1 = "[+]Success new position open : "+str(order['orderId'])+"\nPosition total amount($) : " + str(position_BTC['isolatedWallet']) +'\nentryprice of position : '+ str(position_BTC['entryPrice'])
                print(msg1)

                # Step4. 포지션 종료가 설정
                BTC_tartget_buy_price = int(float(position_BTC['entryPrice']) * BTC_buy_rate)
                print("[i]Set close price of position("+str(BTC_buy_rate)+") : "+str(BTC_tartget_buy_price))
                # step5. 추가 판매가 설정
                BTC_target_sell_price = int(float(position_BTC['entryPrice']) * BTC_sell_rate)
                print("[i]Set add price("+str(BTC_sell_rate)+") : "+str(BTC_target_sell_price))
                # step6. 추가 판매액 설정(현재 포지션 총 구매액 * 1.1(수수료, 소숫점 제외 등 10%정도) * 최초 구매금액)
                BTC_next_amount = int((float(position_BTC['isolatedWallet']) * 1.05 + initamount))
                print("[i]Reset add amount of position($, amount of current position + inital price(about x 2)) : "+str(BTC_next_amount))

                # 잔액 등 확인
                total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                print('[i]Total Asset(before start) : '+ str(total_balance)+'$, Available Asset : '+str(avail_balance)+'$, Margin Asset(Included Profit) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')

            #250초마다 현재 상황 로깅
            price_print_cnt = 0
            while(1):
                #5초에 한번 XRP 가격 확인
                XRP_current_price = client.futures_symbol_ticker(symbol="XRPUSDT")
                BTC_current_price = client.futures_symbol_ticker(symbol="BTCUSDT") 
                
                if price_print_cnt == 0:
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']Current XRP Price : ' + str(XRP_current_price['price'])+ ', Amount of position : '+ str(position_XRP['positionAmt']) + ', Closeprice of position : '+ str(XRP_target_sell_price)+', Target add price : ' +str(XRP_tartget_buy_price))
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']Current BTC Price : ' + str(BTC_current_price['price'])+ ', Amount of position : '+ str(position_BTC['positionAmt']) + ', Closeprice of position : '+ str(BTC_tartget_buy_price)+', Target add price : ' +str(BTC_target_sell_price))
                    price_print_cnt = price_print_cnt + 1
                elif price_print_cnt > 50:
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']Current XRP Price : ' + str(XRP_current_price['price'])+ ', Amount of position : '+ str(position_XRP['positionAmt']) + ', Closeprice of position : '+ str(XRP_target_sell_price)+', Target add price : ' +str(XRP_tartget_buy_price))
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']Current BTC Price : ' + str(BTC_current_price['price'])+ ', Amount of position : '+ str(position_BTC['positionAmt']) + ', Closeprice of position : '+ str(BTC_tartget_buy_price)+', Target add price : ' +str(BTC_target_sell_price))
                    price_print_cnt = 1
                else:
                    price_print_cnt = price_print_cnt + 1
                    pass

                #Step7. XRP(LONG) 추가 구매
                if (float(XRP_current_price['price']) < float(XRP_tartget_buy_price)):
                    symbol = "XRPUSDT"
                    now = datetime.now()
                    print("[d] "+str(int(avail_balance))+", "+str(int(XRP_next_amount)))
                    if avail_balance >= XRP_next_amount:
                        quantity = int(float(XRP_next_amount)/float(XRP_current_price['price'])*7)
                        order = buy_coin(symbol, quantity)
                        time.sleep(5)
                        account = client.futures_account()
                        position_XRP, position_BTC = check_position(account)
                        msg2 = "[+][XRP(Long)]Success Add position : "+str(order['orderId'])+"\nPosition total amount($) : " + str(position_XRP['isolatedWallet']) +'\nentryprice of position: '+ str(position_XRP['entryPrice'])
                        print(msg2)

                        #Step7. 포지션 종료가 및 추가 구매가 재설정
                        XRP_target_sell_price = float(position_XRP['entryPrice']) * XRP_sell_rate
                        print("[i][XRP(Long)]Reset closeprice of position("+str(XRP_sell_rate)+") : "+str(XRP_target_sell_price))
                        XRP_tartget_buy_price = float(position_XRP['entryPrice']) * XRP_buy_rate
                        print("[i][XRP(Long)]Reset addprice of position("+str(XRP_buy_rate)+") : "+str(XRP_tartget_buy_price))
                        #[info] 구매 수량을 1.1이 아닌 1로해서 수수료등 무시하는방식으로, 저렇게 하니깐 금액이 커질수록 너무 커짐, 
                        XRP_next_amount = (float(position_XRP['isolatedWallet']) * 1.05 + initamount)
                        print("[i][XRP(Long)]Reset add amount of position($, Amount of current position + Initial Price(abount x 2)) : "+str(XRP_next_amount))
                        # 잔액 등 확인
                        total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                        print('[i]Total Asset(before start) : '+ str(total_balance)+'$, Available Asset : '+str(avail_balance)+'$, Margin Asset(Included Profit) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')
                    else:
                        print("[-] Failed to add position because of no money.. Available Asset : "+str(avail_balance)+"$, add price of position : "+str(XRP_next_amount))

                #Step8.  XRP(LONG) 포지션 종료
                elif (float(XRP_current_price['price']) > float(XRP_target_sell_price)):
                    symbol = "XRPUSDT"
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']Current XRP Price : ' + str(XRP_current_price['price'])+ ', Amount of current position : '+ str(position_XRP['positionAmt']) + ', closeprice of position : '+ str(XRP_target_sell_price)+', addprice of position : ' +str(XRP_tartget_buy_price))
                    order = sell_coin(symbol, position_XRP['positionAmt'])
                    time.sleep(5)
                    msg3 = "[+][XRP(Long)]Success of close position : "+str(order['orderId'])+"\nPosition total amount($) : " + str(position_XRP['isolatedWallet']) +'\nProfit of closed position : '+ str(round((float(XRP_current_price['price']) - float(position_XRP['entryPrice'])) * float(position_XRP['positionAmt']),2))
                    print(msg3)
                    break
                else:
                    pass


                #Step7. BTC(Short) 추가 판매
                if (float(BTC_current_price['price']) > float(BTC_target_sell_price)):
                    symbol = "BTCUSDT"
                    now = datetime.now()
                    print("[d] "+str(int(avail_balance))+", "+str(int(BTC_next_amount)))
                    if avail_balance >= BTC_next_amount:
                        quantity = round(float(BTC_next_amount)/float(BTC_current_price['price'])*10,3)
                        order = sell_coin(symbol, quantity)
                        time.sleep(5)
                        account = client.futures_account()
                        position_XRP, position_BTC = check_position(account)
                        msg2 = "[+][BTC(Short)]Success Add position : "+str(order['orderId'])+"\nPosition total amount($) : " + str(position_BTC['isolatedWallet']) +'\nentryprice of position : '+ str(position_BTC['entryPrice'])
                        print(msg2)
                        #bot.send_message(chat_id = chat_id, text=msg2, disable_notification=False)

                        #Step7. 포지션 종료가 및 추가 구매가 재설정
                        BTC_tartget_buy_price = int(float(position_BTC['entryPrice']) * BTC_buy_rate)
                        print("[i][BTC(Short)]Reset closeprice of position("+str(BTC_buy_rate)+") : "+str(BTC_tartget_buy_price))
                        BTC_target_sell_price = int(float(position_BTC['entryPrice']) * BTC_sell_rate)
                        print("[i][BTC(Short)]Reset addprice of position("+str(BTC_sell_rate)+") : "+str(BTC_target_sell_price))
                        BTC_next_amount = int((float(position_BTC['isolatedWallet']) * 1.05 + initamount))
                        print("[i][BTC(Short)]Reset add amount of position($, Amount of current position + Initial Price(abount x 2)) : "+str(BTC_next_amount))

                        # 잔액 등 확인
                        total_balance, avail_balance, initialmargin, pnl, roe = check_balance(account)
                        print('[i]Total Asset(before start) : '+ str(total_balance)+'$, Available Asset : '+str(avail_balance)+'$, Margin Asset(Included Profit) : '+str(round(initialmargin, 3))+'$, PNL : '+str(pnl)+'$, ROE : '+str(roe)+'%')
                        #os._exit(1)
                    else:
                        print("[-] Failed to add position because of no money.. Available Asset : "+str(avail_balance)+"$, add price of position : "+str(BTC_next_amount))

                #Step8.  BTC(Short) 포지션 종료
                elif (float(BTC_current_price['price']) < float(BTC_tartget_buy_price)):
                    symbol = "BTCUSDT"
                    now = datetime.now()
                    print('['+now.strftime('%Y-%m-%d %H:%M:%S')+']Current BTC Price : ' + str(BTC_current_price['price'])+ ', Amount of current position : '+ str(position_BTC['positionAmt']) + ', closeprice of position : '+ str(BTC_tartget_buy_price)+', addprice of position : ' +str(BTC_target_sell_price))
                    order = buy_coin(symbol, abs(float(position_BTC['positionAmt'])))
                    time.sleep(5)
                    msg3 = "[+][BTC(Short)]Success of close position : "+str(order['orderId'])+"\nPosition total amount($) : " + str(position_BTC['isolatedWallet']) +'\nprofit of closed position : '+ str(round((float(BTC_current_price['price']) - float(position_BTC['entryPrice'])) * float(position_BTC['positionAmt']),2))
                    print(msg3)
                    #os._exit(1)
                    break
                else:
                    pass

                time.sleep(5)
        except:
            print('[-]Error : Restart')
            time.sleep(15)
            #os._exit(1)
            continue

def main():
    #실시간 가격 확인 및 거래 모듈
    main_transaction()

if __name__ == '__main__':
    api_key, api_secret, XRP_sell_rate, XRP_buy_rate, BTC_sell_rate, BTC_buy_rate = config_read()
    #binance
    api_key = api_key
    api_secret = api_secret
    client = Client(api_key = api_key, api_secret=api_secret, testnet = False)

    main()
