import random

'''
в proxyy прокси с новой строки в формате - http://login:pass@ip:port
в keys приватники с новой строки
rpcs - ваши рпц
delay - от и до скольки секунд между кошельками
moralis api key - https://admin.moralis.io/login регаемся и получаем апи ключ
max_wait_time - cколько максимум по времени ждать в секундах подтверждения транзакции 

'''

with open("keys.txt", "r") as f:
    keys = [row.strip() for row in f]
    random.shuffle(keys)

with open("proxyy.txt", "r") as f:
    proxies = [row.strip() for row in f]

with open("hashes.txt", "r") as f:
    hashes_ = [row.strip() for row in f]

rpcs = {'bsc': 'https://bscrpc.com',
        'polygon': 'https://polygon-rpc.com',
        'core': 'https://rpc.coredao.org',
        'opbnb': 'https://opbnb-testnet-rpc.bnbchain.org'}


DELAY = (0, 100)

MORALIS_API_KEY = ''

max_wait_time = 150


'''
    MESSENGER  -  chain  только из bsc или polygon
                  to  только в bsc, polygon, nova, ftm, mbeam
                  cамый дешевый - в нову

    NFTBRIDGER - для каждой нфт свои чейны, если ошибетесь - работать не будет
    
    CLAIMER - клеймит ваши нфт (которые были забриджены но не были заклеймлены) ВАЖНО УКАЗАТЬ СЕТИ ИЗ И В КАКУЮ БЫЛА ОТПРАВКА!
    
    
    данные ниже для работы в режиме 1 (режим минта & бриджа)

    greenfield   -   сhain - bsc  to - polygon
    zkLightClient   -   сhain - bsc, polygon  to - bsc, polygon
    Mainnet Alpha   -   сhain - polygon, core to - bsc
    Luban   -   сhain - bsc  to - polygon
    ZkBridge on opBNB  -  chain - bsc, polygon, core  to - bsc, polygon, core, opbnb
    
    
    данные ниже для работы в режиме 0 (режим бриджа УЖЕ ЗАБРИДЖЕННЫХ КОГДА ТО НФТ)

    greenfield   -   сhain - polygon  to - bsc
    zkLightClient   -   сhain - bsc, polygon  to - bsc, polygon
    Mainnet Alpha   -   сhain - bsc  to - polygon 
    Luban   -   сhain - polygon  to - bsc
    
    
    TYPE - messenger / nftbridger / claimer (выбираете свой тип)
    
    MODE 0/1/2 - нужен только для режима nftbridger  1 (режим минта & бриджа) / 0 (режим бриджа УЖЕ ЗАБРИДЖЕННЫХ КОГДА ТО НФТ) / 2  (клейм нфт которые не получилось заклеймить ботом) 
    
    NFT - ВЫБОР НАЗВАНИЯ НФТ
'''

TYPE = ''   # 'messenger' / 'nftbridger' / 'claimer'

#chains - bsc / polygon / ftm / core / nova / mbeam / opbnb (самый дешевый для месседжа - nova)

chain = ''
to = '' #or ['chain', 'chain',...] для выбора рандомной сети
MODE = 1   #mode 1 - mint&bridge 0 - bridge already minted nfts / 2 - claim failed nfts
nft = ''  #'greenfield' 'zkLightClient' 'Mainnet Alpha' 'Luban' 'ZkBridge on opBNB' /  ['greenfield','zkLightClient','Mainnet Alpha', 'Luban', 'ZkBridge on opBNB']  - random nft
