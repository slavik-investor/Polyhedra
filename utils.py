import json
import time
from web3 import Web3
import requests
from fake_useragent import UserAgent
from loguru import logger
from eth_account.messages import encode_defunct
from tqdm import tqdm
import pandas as pd
from info import *
from config import *
from eth_utils import *
from moralis import evm_api


class Help:
    def check_status_tx(self, tx_hash):
        logger.info(f'{self.address} - жду подтверждения транзакции  {scans[self.chain]}{self.w3.to_hex(tx_hash)}...')

        start_time = int(time.time())
        while True:
            current_time = int(time.time())
            if current_time >= start_time + max_wait_time:
                logger.info(
                    f'{self.address} - транзакция не подтвердилась за {max_wait_time} cекунд, начинаю повторную отправку...')
                return 0
            try:
                status = self.w3.eth.get_transaction_receipt(tx_hash)['status']
                if status == 1:
                    return status
                time.sleep(1)
            except Exception as error:
                time.sleep(1)

    def sleep_indicator(self, sec):
        for i in tqdm(range(sec), desc='жду', bar_format="{desc}: {n_fmt}c /{total_fmt}c {bar}", colour='green'):
            time.sleep(1)


class ZkBridge(Help):
    def __init__(self, privatekey, delay, chain, to, api, mode, proxy=None):
        self.privatekey = privatekey
        self.chain = chain
        self.to = random.choice(to) if type(to) == list else to
        self.w3 = Web3(Web3.HTTPProvider(rpcs[self.chain]))
        self.account = self.w3.eth.account.from_key(self.privatekey)
        self.address = self.account.address
        self.nft = random.choice(nft) if type(nft) == list else nft
        self.delay = delay
        self.proxy = proxy
        self.mode = mode
        self.moralisapi = api
        self.nft_address = nfts_addresses[self.nft][self.chain] if self.mode == 1 else \
            reversed_nfts_addresses[self.nft][self.chain] if self.mode == 0 else ''
        self.bridge_address = nft_bridge_addresses[self.chain]

    def auth(self):
        ua = UserAgent()
        ua = ua.random
        headers = {
            'authority': 'api.zkbridge.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://zkbridge.com',
            'referer': 'https://zkbridge.com/',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': ua,
        }

        json_data = {
            'publicKey': self.address.lower(),
        }
        while True:
            try:
                if self.proxy:
                    proxies = {'http': self.proxy, 'https': self.proxy}
                    response = requests.post(
                        'https://api.zkbridge.com/api/signin/validation_message',
                        json=json_data, headers=headers, proxies=proxies
                    )
                else:
                    response = requests.post(
                        'https://api.zkbridge.com/api/signin/validation_message',
                        json=json_data, headers=headers,

                    )

                if response.status_code == 200:
                    msg = json.loads(response.text)
                    msg = msg['message']
                    msg = encode_defunct(text=msg)
                    sign = self.w3.eth.account.sign_message(msg, private_key=self.privatekey)
                    signature = self.w3.to_hex(sign.signature)
                    json_data = {
                        'publicKey': self.address,
                        'signedMessage': signature,
                    }
                    return signature, ua
            except Exception as e:
                logger.error(f'{self.address}:{self.chain} - {e}')
                time.sleep(5)

    def sign(self):
        # sign msg
        signature, ua = self.auth()
        headers = {
            'authority': 'api.zkbridge.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://zkbridge.com',
            'referer': 'https://zkbridge.com/',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': ua,
        }

        json_data = {
            'publicKey': self.address.lower(),
            'signedMessage': signature,
        }
        while True:
            try:

                if self.proxy:
                    proxies = {'http': self.proxy, 'https': self.proxy}

                    response = requests.post('https://api.zkbridge.com/api/signin', headers=headers, json=json_data,
                                             proxies=proxies)
                else:
                    response = requests.post('https://api.zkbridge.com/api/signin', headers=headers, json=json_data)
                if response.status_code == 200:
                    token = json.loads(response.text)['token']
                    headers['authorization'] = f'Bearer {token}'
                    session = requests.session()
                    session.headers.update(headers)
                    return session

            except Exception as e:
                logger.error(F'{self.address}:{self.chain} - {e}')
                time.sleep(5)

    def profile(self):
        session = self.sign()
        params = ''
        try:
            if self.proxy:
                proxies = {'http': self.proxy, 'https': self.proxy}
                response = session.get('https://api.zkbridge.com/api/user/profile', params=params, proxies=proxies)
            else:
                response = session.get('https://api.zkbridge.com/api/user/profile', params=params)
            if response.status_code == 200:
                logger.success(f'{self.address}:{self.chain} - успешно авторизовался...')
                return session
        except Exception as e:
            logger.error(f'{self.address}:{self.chain} - {e}')
            return False

    def balance_and_get_id(self):
        if self.chain != 'core':
            try:
                api_key = self.moralisapi
                params = {
                    "chain": self.chain,
                    "format": "decimal",
                    "token_addresses": [
                        self.nft_address
                    ],
                    "media_items": False,
                    "address": self.address}

                result = evm_api.nft.get_wallet_nfts(api_key=api_key, params=params)
                id_ = int(result['result'][0]['token_id'])
                if id_:
                    logger.success(f'{self.address}:{self.chain} - успешно найдена {self.nft} {id_}...')
                    return id_
            except Exception as e:
                if 'list index out of range' in str(e):
                    logger.error(f'{self.address}:{self.chain} - на кошельке отсутсвует {self.nft}...')
                    return None
                else:
                    logger.error(f'{self.address}:{self.chain} - {e}...')
        else:
            try:
                contract = self.w3.eth.contract(address=self.nft_address, abi=zk_nft_abi)
                balance = contract.functions.balanceOf(self.address).call()
                if balance > 0:
                    totalSupply = contract.functions.totalSupply().call()
                    id_ = contract.functions.tokensOfOwnerIn(self.address, totalSupply - 100, totalSupply).call()[0]
                    return id_
                else:
                    logger.error(f'{self.address}:{self.chain} - на кошельке отсутсвует {self.nft}...')
                    return None
            except Exception as e:
                logger.error(f'{self.address}:{self.chain} - {e}...')

    def add_hash_and_address(self, hash_):
        with open("hashes.txt", "w") as file:
            file.write(f"{self.privatekey}:{hash_}\n")

    def mint(self):
        while True:
            zkNft = self.w3.eth.contract(address=Web3.to_checksum_address(self.nft_address), abi=zk_nft_abi)

            session = self.profile()
            if not session:
                return False
            try:
                if session:
                    nonce = self.w3.eth.get_transaction_count(self.address)
                    time.sleep(2)
                    tx = zkNft.functions.mint().build_transaction({
                        'from': self.address,
                        'gas': zkNft.functions.mint().estimate_gas(
                            {'from': self.address, 'nonce': nonce}),
                        'nonce': nonce,
                        'maxFeePerGas': int(self.w3.eth.gas_price),
                        'maxPriorityFeePerGas': int(self.w3.eth.gas_price*0.8)
                    })
                    if self.chain == 'bsc' or self.chain == 'core':
                        del tx['maxFeePerGas']
                        del tx['maxPriorityFeePerGas']
                        tx['gasPrice'] = self.w3.eth.gas_price

                    logger.info(f'{self.address}:{self.chain} - начинаю минт {self.nft}...')
                    sign = self.account.sign_transaction(tx)
                    hash = self.w3.eth.send_raw_transaction(sign.rawTransaction)
                    status = self.check_status_tx(hash)
                    self.sleep_indicator(5)
                    if status == 1:
                        logger.success(
                            f'{self.address}:{self.chain} - успешно заминтил {self.nft} : {scans[self.chain]}{self.w3.to_hex(hash)}...')
                        self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                        return session
                    else:
                        logger.info(f'{self.address}:{self.chain} - пробую минт еще раз...')
                        self.mint()
            except Exception as e:
                error = str(e)
                if 'nonce too low' in error or 'already known' in error:
                    logger.success(f'{self.address}:{self.chain} - ошибка при минте, пробую еще раз...')
                    time.sleep(10)
                    self.mint()
                if 'INTERNAL_ERROR: insufficient funds' in error or 'insufficient funds for gas * price + value' in error:
                    logger.error(
                        f'{self.address}:{self.chain} - не хватает денег на газ, заканчиваю работу через 5 секунд...')
                    time.sleep(5)
                    return False
                elif 'Each address may claim one NFT only. You have claimed already' in error:
                    logger.error(f'{self.address}:{self.chain} - {self.nft} можно клеймить только один раз!...')
                    return False
                else:
                    logger.error(f'{self.address}:{self.chain} - {e}...')
                    return False

    def bridge_nft(self):
        if self.mode == 1:
            id_ = self.balance_and_get_id()
            session = self.profile()
            if session:
                session = session

            if id_ == None:
                session = self.mint()
                if session:
                    time.sleep(5)
                    id_ = self.balance_and_get_id()
                    if id_ == None:
                        return False
                else:
                    return False
        else:
            session = self.profile()
            id_ = self.balance_and_get_id()

        zkNft = self.w3.eth.contract(address=Web3.to_checksum_address(self.nft_address), abi=zk_nft_abi)

        def approve_nft(gwei=None):
            # approve
            while True:
                if id_:
                    try:
                        nonce = self.w3.eth.get_transaction_count(self.address)
                        time.sleep(2)
                        tx = zkNft.functions.approve(
                            Web3.to_checksum_address(Web3.to_checksum_address('0x3668c325501322CEB5a624E95b9E16A019cDEBe8'.lower())), id_).build_transaction({
                            'from': self.address,
                            'gas': zkNft.functions.approve(Web3.to_checksum_address('0x3668c325501322CEB5a624E95b9E16A019cDEBe8'.lower()),
                                                           id_).estimate_gas({'from': self.address, 'nonce': nonce}),
                            'nonce': nonce,
                            'maxFeePerGas': int(self.w3.eth.gas_price),
                            'maxPriorityFeePerGas': int(self.w3.eth.gas_price*0.8)
                        })
                        if self.chain == 'bsc' or self.chain == 'core':
                            del tx['maxFeePerGas']
                            del tx['maxPriorityFeePerGas']
                            tx['gasPrice'] = self.w3.eth.gas_price
                        logger.info(f'{self.address}:{self.chain} - начинаю апрув {self.nft} {id_}...')
                        sign = self.account.sign_transaction(tx)
                        hash = self.w3.eth.send_raw_transaction(sign.rawTransaction)
                        status = self.check_status_tx(hash)
                        self.sleep_indicator(5)
                        if status == 1:
                            logger.success(
                                f'{self.address}:{self.chain} - успешно апрувнул {self.nft} {id_} : {scans[self.chain]}{self.w3.to_hex(hash)}...')
                            self.sleep_indicator(random.randint(1, 10))
                            return True
                        else:
                            logger.info(f'{self.address}:{self.chain} - пробую апрув еще раз...')
                            approve_nft()
                    except Exception as e:
                        error = str(e)
                        if 'nonce too low' in error or 'already known' in error:
                            logger.info(f'{self.address}:{self.chain} - ошибка при апруве, пробую еще раз...')
                            approve_nft()
                        if 'INTERNAL_ERROR: insufficient funds' in error or 'insufficient funds for gas * price + value' in error:
                            logger.error(
                                f'{self.address}:{self.chain} - не хватает денег на газ, заканчиваю работу через 5 секунд...')
                            time.sleep(5)
                            return False
                        else:
                            logger.error(f'{self.address}:{self.chain} - {e}...')
                            time.sleep(2)
                            return False

        def bridge_():
            address_contracta = "0x3668c325501322CEB5a624E95b9E16A019cDEBe8".lower()
            bridge_abi_my = '[{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint8","name":"version","type":"uint8"}],"name":"Initialized","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"indexed":false,"internalType":"uint64","name":"_nonce","type":"uint64"},{"indexed":false,"internalType":"bytes","name":"_payload","type":"bytes"},{"indexed":false,"internalType":"bytes","name":"_reason","type":"bytes"}],"name":"MessageFailed","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint64","name":"sequence","type":"uint64"},{"indexed":false,"internalType":"address","name":"sourceToken","type":"address"},{"indexed":false,"internalType":"address","name":"token","type":"address"},{"indexed":false,"internalType":"uint256","name":"tokenID","type":"uint256"},{"indexed":false,"internalType":"uint16","name":"sourceChain","type":"uint16"},{"indexed":false,"internalType":"uint16","name":"sendChain","type":"uint16"},{"indexed":false,"internalType":"address","name":"recipient","type":"address"}],"name":"ReceiveNFT","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"indexed":false,"internalType":"uint64","name":"_nonce","type":"uint64"},{"indexed":false,"internalType":"bytes32","name":"_payloadHash","type":"bytes32"}],"name":"RetryMessageSuccess","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"indexed":false,"internalType":"uint16","name":"_type","type":"uint16"},{"indexed":false,"internalType":"uint256","name":"_minDstGas","type":"uint256"}],"name":"SetMinDstGas","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_remoteChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_path","type":"bytes"}],"name":"SetTrustedRemote","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint16","name":"_remoteChainId","type":"uint16"},{"indexed":false,"internalType":"bytes","name":"_remoteAddress","type":"bytes"}],"name":"SetTrustedRemoteAddress","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint64","name":"sequence","type":"uint64"},{"indexed":false,"internalType":"address","name":"token","type":"address"},{"indexed":false,"internalType":"uint256","name":"tokenID","type":"uint256"},{"indexed":false,"internalType":"uint16","name":"recipientChain","type":"uint16"},{"indexed":false,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"address","name":"recipient","type":"address"}],"name":"TransferNFT","type":"event"},{"inputs":[{"internalType":"bytes","name":"_encoded","type":"bytes"}],"name":"_parseTransfer","outputs":[{"components":[{"internalType":"address","name":"tokenAddress","type":"address"},{"internalType":"uint16","name":"tokenChain","type":"uint16"},{"internalType":"bytes32","name":"symbol","type":"bytes32"},{"internalType":"bytes32","name":"name","type":"bytes32"},{"internalType":"uint256","name":"tokenID","type":"uint256"},{"internalType":"string","name":"uri","type":"string"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint16","name":"toChain","type":"uint16"}],"internalType":"struct NFT721Bridge.Transfer721","name":"transfer","type":"tuple"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint16","name":"","type":"uint16"}],"name":"chainFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"chainId","outputs":[{"internalType":"uint16","name":"","type":"uint16"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"uint256","name":"_tokenId","type":"uint256"},{"internalType":"uint16","name":"_recipientChain","type":"uint16"},{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"bytes","name":"_adapterParams","type":"bytes"}],"name":"estimateFee","outputs":[{"internalType":"uint256","name":"fee","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"","type":"uint16"},{"internalType":"bytes","name":"","type":"bytes"},{"internalType":"uint64","name":"","type":"uint64"}],"name":"failedMessages","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"}],"name":"forceResumeReceive","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"},{"internalType":"uint16","name":"_chainId","type":"uint16"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"_configType","type":"uint256"}],"name":"getConfig","outputs":[{"internalType":"bytes","name":"","type":"bytes"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_remoteChainId","type":"uint16"}],"name":"getTrustedRemoteAddress","outputs":[{"internalType":"bytes","name":"","type":"bytes"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_chainId","type":"uint16"},{"internalType":"address","name":"_endpoint","type":"address"}],"name":"initialize","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"}],"name":"isTrustedRemote","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"lzEndpoint","outputs":[{"internalType":"contract ILayerZeroEndpoint","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"internalType":"uint64","name":"_nonce","type":"uint64"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"lzReceive","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"internalType":"uint64","name":"_nonce","type":"uint64"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"nonblockingLzReceive","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"operator","type":"address"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bytes","name":"","type":"bytes"}],"name":"onERC721Received","outputs":[{"internalType":"bytes4","name":"","type":"bytes4"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_srcAddress","type":"bytes"},{"internalType":"uint64","name":"_nonce","type":"uint64"},{"internalType":"bytes","name":"_payload","type":"bytes"}],"name":"retryMessage","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"},{"internalType":"uint16","name":"_chainId","type":"uint16"},{"internalType":"uint256","name":"_configType","type":"uint256"},{"internalType":"bytes","name":"_config","type":"bytes"}],"name":"setConfig","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_dstChainId","type":"uint16"},{"internalType":"uint256","name":"_fee","type":"uint256"}],"name":"setFee","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_lzEndpoint","type":"address"}],"name":"setLzEndpoint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"}],"name":"setReceiveVersion","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_version","type":"uint16"}],"name":"setSendVersion","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_srcChainId","type":"uint16"},{"internalType":"bytes","name":"_path","type":"bytes"}],"name":"setTrustedRemote","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_remoteChainId","type":"uint16"},{"internalType":"bytes","name":"_remoteAddress","type":"bytes"}],"name":"setTrustedRemoteAddress","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"_nativeChainId","type":"uint16"},{"internalType":"address","name":"_nativeContract","type":"address"},{"internalType":"address","name":"_wrapper","type":"address"}],"name":"setWrappedAsset","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_token","type":"address"},{"internalType":"uint256","name":"_tokenId","type":"uint256"},{"internalType":"uint16","name":"_recipientChain","type":"uint16"},{"internalType":"address","name":"_recipient","type":"address"},{"internalType":"bytes","name":"_adapterParams","type":"bytes"}],"name":"transferNFT","outputs":[{"internalType":"uint64","name":"sequence","type":"uint64"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint16","name":"","type":"uint16"}],"name":"trustedRemoteLookup","outputs":[{"internalType":"bytes","name":"","type":"bytes"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"wrappedAssetData","outputs":[{"internalType":"uint16","name":"nativeChainId","type":"uint16"},{"internalType":"address","name":"nativeContract","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint16","name":"","type":"uint16"},{"internalType":"address","name":"","type":"address"}],"name":"wrappedAssets","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]'
            bridge = self.w3.eth.contract(address=Web3.to_checksum_address(address_contracta), abi=bridge_abi_my)
            to = chain_ids[self.to]
            
            enco = f'0x000100000000000000000000000000000000000000000000000000000000001b7740'
            fee = bridge.functions.estimateFee(
            Web3.to_checksum_address(self.nft_address),
            id_,
            to,
            self.address,
            enco
            ).call()
            logger.info(f'{self.address}:{self.chain} - начинаю бридж {self.nft} {id_}...')
            while True:
                try:
                    nonce = self.w3.eth.get_transaction_count(self.address)
                    time.sleep(2)
                    tx = bridge.functions.transferNFT(
                        Web3.to_checksum_address(self.nft_address),
                        id_,
                        to,
                        self.address,
                        enco
                        ).build_transaction({
                        'from': self.address,
                        'value': fee,
                        'gas': bridge.functions.transferNFT(
                        Web3.to_checksum_address(self.nft_address),
                        id_,
                        to,
                        self.address,
                        enco).estimate_gas({'from': self.address, 'nonce': nonce, 'value': fee}),
                        'nonce': nonce,
                        'maxFeePerGas': int(self.w3.eth.gas_price),
                        'maxPriorityFeePerGas': int(self.w3.eth.gas_price*0.8)
                    })
                    if self.chain == 'bsc' or self.chain == 'core':
                        del tx['maxFeePerGas']
                        del tx['maxPriorityFeePerGas']
                        tx['gasPrice'] = self.w3.eth.gas_price
                    sign = self.account.sign_transaction(tx)
                    hash = self.w3.eth.send_raw_transaction(sign.rawTransaction)
                    status = self.check_status_tx(hash)
                    self.sleep_indicator(5)
                    if status == 1:
                        logger.success(
                            f'{self.address}:{self.chain} - успешно бриджанул {self.nft} {id_} : {scans[self.chain]}{self.w3.to_hex(hash)}...')
                        self.sleep_indicator(random.randint(1, 20))
                        return self.w3.to_hex(hash), session, id_
                    else:
                        logger.info(f'{self.address}:{self.chain} - пробую бриджить еще раз...')
                        bridge_()
                except Exception as e:
                    error = str(e)
                    if 'INTERNAL_ERROR: insufficient funds' in error or 'insufficient funds for gas * price + value' in error:
                        logger.error(
                            f'{self.address}:{self.chain} - не хватает денег на газ, заканчиваю работу через 5 секунд...')
                        time.sleep(5)
                        return False
                    if 'nonce too low' in error or 'already known' in error:
                        logger.info(f'{self.address}:{self.chain} - ошибка при бридже, пробую еще раз...')
                        bridge_()
                    else:
                        logger.error(f'{self.address}:{self.chain} - {e}')
                        return False

        if approve_nft(self):
            return bridge_()
        else:
            return False

    def go_requests(self, hash, session, nft_id):
        def create_order():
            json_data = {
                'from': self.address.lower(),
                'to': self.address.lower(),
                'sourceChainId': ids[self.chain],
                'targetChainId': ids[self.to],
                'txHash': hash,
                'contracts': [
                    {
                        'contractAddress': self.nft_address,
                        'tokenId': nft_id,
                    },
                ],
            }
            while True:
                try:
                    if self.proxy:
                        proxies = {'http': self.proxy, 'https': self.proxy}
                        response = session.post('https://api.zkbridge.com/api/bridge/createOrder', json=json_data,
                                                proxies=proxies)
                    else:
                        response = session.post('https://api.zkbridge.com/api/bridge/createOrder', json=json_data)
                    if response.status_code == 200:
                        id_ = json.loads(response.text)['id']
                        return id_
                except Exception as e:
                    logger.error(f'{self.address}:{self.chain}- {e}')
                    time.sleep(5)

        def gen_blob():
            data = create_order()
            if data:
                id_ = data
            else:
                return False
            json_data = {
                'tx_hash': hash,
                'chain_id': chain_ids[self.chain],
                'testnet': False,
            }
            while True:
                try:
                    if self.proxy:
                        proxies = {'http': self.proxy, 'https': self.proxy}
                        response = session.post('https://api.zkbridge.com/api/v2/receipt_proof/generate',
                                                json=json_data,
                                                proxies=proxies)
                    else:
                        response = session.post('https://api.zkbridge.com/api/v2/receipt_proof/generate',
                                                json=json_data)
                    if response.status_code == 200:
                        data_ = json.loads(response.text)
                        logger.success(f'{self.address} - сгенерирован blob для клейма...')
                        return data_, id_, session

                except Exception as e:
                    logger.error(f'{self.address}:{self.to}- {e}')
                    time.sleep(5)

        return gen_blob()

    def claimOrder(self, session, id, hash):
        json_data = {
            'claimHash': hash,
            'id': id,
        }
        while True:
            try:
                if self.proxy:
                    proxies = {'http': self.proxy, 'https': self.proxy}
                    response = session.post('https://api.zkbridge.com/api/bridge/claimOrder', json=json_data,
                                            proxies=proxies)
                else:
                    response = session.post('https://api.zkbridge.com/api/bridge/claimOrder', json=json_data)
                if response.status_code == 200:
                    logger.success(f'{self.address} - успешно забриджено!...')
                    self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                    return True

            except Exception as e:
                logger.error(f'{self.address}:{self.to} - {e}')
                time.sleep(5)

    def check_status_tx2(self, w3, tx_hash):
        logger.info(f'{self.address} - жду подтверждения транзакции {scans[self.to]}{w3.to_hex(tx_hash)}...')
        start_time = int(time.time())
        while True:
            current_time = int(time.time())
            if current_time >= start_time + max_wait_time:
                logger.info(
                    f'{self.address} - транзакция не подтвердилась за {max_wait_time} cекунд, начинаю повторную отправку...')
                return 0
            try:
                status = w3.eth.get_transaction_receipt(tx_hash)['status']
                if status == 1:
                    return status
                time.sleep(1)
            except Exception as error:
                time.sleep(1)

    def redeem_nft(self, session=None, hash_=None):
        if self.mode == 2:
            data = self.profile()
            if data:
                session = data
            else:
                self.add_hash_and_address(hash_)
                return self.address, f'error'

        def get_order_by_hash():
            logger.info(f'{self.address}:{self.to} - пробую делать redeem {self.nft} в сети назначения...')
            while True:
                params = {
                    'depositHash': hash_,
                    'sourceChainId': ids[self.chain],
                }
                try:
                    if self.proxy:
                        proxies = {'http': self.proxy, 'https': self.proxy}
                        response = session.get('https://api.zkbridge.com/api/bridge/getOrderByDepositHashAndChainId',
                                               params=params, proxies=proxies)
                    else:
                        response = session.get('https://api.zkbridge.com/api/bridge/getOrderByDepositHashAndChainId',
                                               params=params)

                    if response.status_code == 200:
                        data = json.loads(response.text)
                        if data['message'] == 'success':
                            id_ = data['data']['id']
                            logger.success(
                                f'{self.address} - успешно нашел информацию для клейма {self.nft} в сети назначения...')
                            time.sleep(5)
                            return id_

                except Exception as e:
                    logger.error(f'{self.address}:{self.to} - {e}')
                    time.sleep(5)

        def gen_blob():
            data = get_order_by_hash()
            if data:
                id_ = data
            else:
                return False
            json_data = {
                'tx_hash': hash_,
                'chain_id': chain_ids[self.chain],
                'testnet': False,
            }
            while True:
                try:
                    if self.proxy:
                        proxies = {'http': self.proxy, 'https': self.proxy}
                        response = session.post('https://api.zkbridge.com/api/v2/receipt_proof/generate',
                                                json=json_data,
                                                proxies=proxies)
                    else:
                        response = session.post('https://api.zkbridge.com/api/v2/receipt_proof/generate',
                                                json=json_data)
                    if response.status_code == 200:
                        data_ = json.loads(response.text)
                        logger.success(f'{self.address} - сгенерирован blob для клейма {self.nft}...')
                        time.sleep(5)
                        return data_, id_, session

                except Exception as e:
                    logger.error(f'{self.address}:{self.to} - {e}')
                    time.sleep(5)

        def claim_again():
            w3 = Web3(Web3.HTTPProvider(rpcs[self.to]))
            account = w3.eth.account.from_key(self.privatekey)
            address = account.address
            claim = w3.eth.contract(address=Web3.to_checksum_address(nft_claim_addresses[self.to]), abi=zk_claim_abi)
            while True:
                data = gen_blob()
                if data:
                    data_, id_, session = data
                else:
                    return address, False
                cid = data_['chain_id']
                proof = data_['proof_index']
                blob = data_['proof_blob']
                block_hash = data_['block_hash']
                try:
                    nonce = w3.eth.get_transaction_count(address)
                    time.sleep(2)

                    tx = claim.functions.validateTransactionProof(cid, to_bytes(hexstr=block_hash), proof,
                                                                  to_bytes(hexstr=blob)).build_transaction({
                        'from': address,
                        'gas': claim.functions.validateTransactionProof(cid, to_bytes(hexstr=block_hash), proof,
                                                                        to_bytes(hexstr=blob)).estimate_gas(
                            {'from': address, 'nonce': nonce}),
                        'nonce': nonce,
                        'maxFeePerGas': int(w3.eth.gas_price),
                        'maxPriorityFeePerGas': int(w3.eth.gas_price*0.8)
                    })
                    if self.to == 'bsc' or self.to == 'core':
                        del tx['maxFeePerGas']
                        del tx['maxPriorityFeePerGas']
                        tx['gasPrice'] = w3.eth.gas_price
                    sign = account.sign_transaction(tx)
                    hash = w3.eth.send_raw_transaction(sign.rawTransaction)
                    status = self.check_status_tx2(w3, hash)
                    self.sleep_indicator(10)
                    if status == 1:
                        logger.success(
                            f'{address}:{self.to} - успешно заклеймил {self.nft} : {scans[self.to]}{w3.to_hex(hash)}...')
                        order = self.claimOrder(session, id_, block_hash)
                        if order:
                            return address, 'success'
                        else:
                            self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                            self.add_hash_and_address(hash_)
                            return address, 'error'
                    else:
                        logger.info(f'{self.address}:{self.chain} - пробую клеймить еще раз...')
                        claim_again()

                except Exception as e:
                    error = str(e)
                    if 'execution reverted: Block Header is not set' in error:
                        logger.info(f'{address}:{self.to} - {self.to} лагает, пробую еще раз...')
                        tt = random.randint(20, 60)
                        logger.info(f'{address}:{self.to} - cплю {tt} секунд...')
                        self.sleep_indicator(tt)
                    elif 'nonce too low' in error or 'already known' in error or 'Message already executed' in error:
                        logger.success(f'{self.address}:{self.to} - пробую клеймить еще раз...')
                        claim_again()
                    elif 'INTERNAL_ERROR: insufficient funds' in error or 'insufficient funds for gas * price + value' in error:
                        logger.error(
                            f'{self.address}:{self.to} - не хватает денег на газ, заканчиваю работу через 5 секунд...')
                        time.sleep(5)
                        self.add_hash_and_address(hash_)
                        return address, f'error {hash_}'
                    else:
                        logger.error(f'{address}:{self.to} - {e} ...')
                        self.add_hash_and_address(hash_)
                        return address, f'error {hash_}'

        claim_again()

    def claim_on_destinaton(self):
        w3 = Web3(Web3.HTTPProvider(rpcs[self.to]))
        account = w3.eth.account.from_key(self.privatekey)
        address = account.address
        claim = w3.eth.contract(address=Web3.to_checksum_address(nft_claim_addresses[self.to]), abi=zk_claim_abi)

        data = self.bridge_nft()
        if data:
            hash_, session, nft_id = data
        else:
            return address, 'error'

        while True:
            data = self.go_requests(hash_, session, nft_id)
            if data:
                data_, id_, session = data
            else:
                return address, 'error'
            cid = data_['chain_id']
            proof = data_['proof_index']
            blob = data_['proof_blob']
            block_hash = data_['block_hash']
            try:
                nonce = w3.eth.get_transaction_count(address)
                time.sleep(2)
                tx = claim.functions.validateTransactionProof(cid, to_bytes(hexstr=block_hash), proof,
                                                              to_bytes(hexstr=blob)).build_transaction({
                    'from': address,
                    'gas': claim.functions.validateTransactionProof(cid, to_bytes(hexstr=block_hash), proof,
                                                                    to_bytes(hexstr=blob)).estimate_gas(
                        {'from': address, 'nonce': nonce}),
                    'nonce': nonce,
                    'maxFeePerGas': int(w3.eth.gas_price),
                    'maxPriorityFeePerGas': int(w3.eth.gas_price*0.8)
                })
                if self.to == 'bsc' or self.to == 'core':
                    del tx['maxFeePerGas']
                    del tx['maxPriorityFeePerGas']
                    tx['gasPrice'] = w3.eth.gas_price
                sign = account.sign_transaction(tx)
                hash = w3.eth.send_raw_transaction(sign.rawTransaction)
                status = self.check_status_tx2(w3, hash)
                self.sleep_indicator(10)
                if status == 1:
                    logger.success(
                        f'{address}:{self.to} - успешно заклеймил {self.nft} : {scans[self.to]}{w3.to_hex(hash)}...')
                    order = self.claimOrder(session, id_, block_hash)
                    if order:
                        return address, 'success'
                    else:
                        self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                        self.add_hash_and_address(hash_)
                        return address, 'error'
                else:
                    logger.info(f'{self.address}:{self.chain} - пробую клеймить через redeem еще раз...')
                    self.redeem_nft(session, hash_)

            except Exception as e:
                error = str(e)
                if 'execution reverted: Block Header is not set' in error:
                    logger.info(f'{address}:{self.to} - {self.to} лагает, пробую еще раз...')
                    tt = random.randint(20, 60)
                    logger.info(f'{address}:{self.to} - cплю {tt} секунд...')
                    self.sleep_indicator(tt)
                elif 'nonce too low' in error or 'already known' in error or 'Message already executed' in error:
                    logger.success(f'{self.address}:{self.to} - успешно заклеймил {self.nft}...')
                    self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                    order = self.claimOrder(session, id_, block_hash)
                    if order:
                        self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                        return address, 'success'
                    else:
                        self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                        return address, f'error {hash_}'
                elif 'INTERNAL_ERROR: insufficient funds' in error or 'insufficient funds for gas * price + value' in error:
                    logger.error(
                        f'{self.address}:{self.to} - не хватает денег на газ, заканчиваю работу через 5 секунд...')
                    time.sleep(5)
                    self.add_hash_and_address(hash_)
                    return address, f'error {hash_}'
                else:
                    logger.error(f'{address}:{self.to} - {e} ...')
                    self.redeem_nft(session, hash_)


class ZkMessage(Help):
    def __init__(self, privatekey, chain, to, delay, proxy=None):
        self.privatekey = privatekey
        self.chain = chain
        self.to = random.choice(to) if type(to) == list else to
        self.w3 = Web3(Web3.HTTPProvider(rpcs[self.chain]))
        self.scan = scans[self.chain]
        self.account = self.w3.eth.account.from_key(self.privatekey)
        self.address = self.account.address
        self.delay = delay
        self.proxy = proxy

    def auth(self):
        ua = UserAgent()
        ua = ua.random
        headers = {
            'authority': 'api.zkbridge.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://zkbridge.com',
            'referer': 'https://zkbridge.com/',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': ua,
        }

        json_data = {
            'publicKey': self.address.lower(),
        }

        while True:
            try:
                if self.proxy:
                    proxies = {'http': self.proxy, 'https': self.proxy}
                    response = requests.post(
                        'https://api.zkbridge.com/api/signin/validation_message',
                        json=json_data, headers=headers, proxies=proxies
                    )
                else:
                    response = requests.post(
                        'https://api.zkbridge.com/api/signin/validation_message',
                        json=json_data, headers=headers,

                    )

                if response.status_code == 200:
                    msg = json.loads(response.text)

                    msg = msg['message']
                    msg = encode_defunct(text=msg)
                    sign = self.w3.eth.account.sign_message(msg, private_key=self.privatekey)
                    signature = self.w3.to_hex(sign.signature)
                    json_data = {
                        'publicKey': self.address,
                        'signedMessage': signature,
                    }
                    return signature, ua
            except Exception as e:
                logger.error(f'{self.address}:{self.chain} - {e}')
                time.sleep(5)

    def sign(self):

        # sign msg
        signature, ua = self.auth()
        headers = {
            'authority': 'api.zkbridge.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'origin': 'https://zkbridge.com',
            'referer': 'https://zkbridge.com/',
            'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': ua,
        }

        json_data = {
            'publicKey': self.address.lower(),
            'signedMessage': signature,
        }
        while True:
            try:

                if self.proxy:
                    proxies = {'http': self.proxy, 'https': self.proxy}

                    response = requests.post('https://api.zkbridge.com/api/signin', headers=headers, json=json_data,
                                             proxies=proxies)
                else:
                    response = requests.post('https://api.zkbridge.com/api/signin', headers=headers, json=json_data)
                if response.status_code == 200:
                    token = json.loads(response.text)['token']
                    headers['authorization'] = f'Bearer {token}'
                    session = requests.session()
                    session.headers.update(headers)
                    return session

            except Exception as e:
                logger.error(F'{self.address}:{self.chain} - {e}')
                time.sleep(5)

    def profile(self):
        session = self.sign()
        params = ''
        try:
            if self.proxy:
                proxies = {'http': self.proxy, 'https': self.proxy}
                response = session.get('https://api.zkbridge.com/api/user/profile', params=params, proxies=proxies)
            else:
                response = session.get('https://api.zkbridge.com/api/user/profile', params=params)
            if response.status_code == 200:
                logger.success(f'{self.address}:{self.chain} - успешно авторизовался...')
                return session
        except Exception as e:
            logger.error(f'{self.address}:{self.chain} - {e}')
            return False

    def check_status_lz(self):
        contract_msg = Web3.to_checksum_address(sender_msgs[self.chain])
        mailer = self.w3.eth.contract(address=contract_msg, abi=mailer_abi)

        if not mailer.functions.layerZeroPaused().call():
            logger.success(f'{self.address}:{self.chain} - L0 активен...')
            return True
        else:
            logger.info(f'{self.address}:{self.chain} - L0 не активен...')
            return False

    def msg(self, session, contract_msg, msg, from_chain, to_chain, tx_hash):

        timestamp = time.time()

        json_data = {
            'message': msg,
            'mailSenderAddress': contract_msg,
            'receiverAddress': self.address,
            'receiverChainId': to_chain,
            'sendTimestamp': timestamp,
            'senderAddress': self.address,
            'senderChainId': from_chain,
            'senderTxHash': tx_hash,
            'sequence': random.randint(4500, 5000),
            'receiverDomainName': '',
        }

        try:
            if self.proxy:
                proxies = {'http': self.proxy, 'https': self.proxy}
                response = session.get('https://api.zkbridge.com/api/user/profile', json=json_data, proxies=proxies)
            else:
                response = session.get('https://api.zkbridge.com/api/user/profile', json=json_data)
            if response.status_code == 200:
                logger.success(f'{self.address}:{self.chain} - cообщение подтвержденно...')
                return True


        except Exception as e:
            logger.error(f'{self.address}:{self.chain} - {e}')
            return False

    def create_msg(self):
        n = random.randint(1, 10)
        string = []
        word_site = "https://www.mit.edu/~ecprice/wordlist.10000"
        response = requests.get(word_site)
        for i in range(n):
            WORDS = [g for g in response.text.split()]
            string.append(random.choice(WORDS))

        msg = ' '.join(string)
        return msg

    def send_msg(self):
        data = self.profile()
        if data:
            session = data
        else:
            return False

        contract_msg = Web3.to_checksum_address(sender_msgs[self.chain])
        lz_id = stargate_ids[self.to]
        to_chain_id = chain_ids[self.to]
        from_chain_id = chain_ids[self.chain]
        message = self.create_msg()
        dst_address = Web3.to_checksum_address(dst_addresses[self.to])
        lzdst_address = Web3.to_checksum_address(lzdst_addresses[self.to])
        mailer = self.w3.eth.contract(address=contract_msg, abi=mailer_abi)

        native_ = native[self.chain]
        zkFee = mailer.functions.fees(to_chain_id).call()

        while True:
            lz_status = self.check_status_lz()
            if lz_status:
                fee = mailer.functions.estimateLzFee(lz_id, self.address, message).call()
                value = fee + zkFee
                logger.info(
                    f'{self.address}:{self.chain} - начинаю отправку сообщения в {self.to} через L0, предполагаемая комса - {(fee + zkFee) / 10 ** 18} {native_}...')
                try:
                    tx = mailer.functions.sendMessage(to_chain_id, dst_address, lz_id, lzdst_address, fee, self.address,
                                                      message).build_transaction({
                        'from': self.address,
                        'value': value,
                        'gas': mailer.functions.sendMessage(to_chain_id, dst_address, lz_id, lzdst_address, fee,
                                                            self.address,
                                                            message).estimate_gas(
                            {'from': self.address, 'nonce': self.w3.eth.get_transaction_count(self.address),
                             'value': value}),
                        'nonce': self.w3.eth.get_transaction_count(self.address),
                        'maxFeePerGas': int(self.w3.eth.gas_price),
                        'maxPriorityFeePerGas': int(self.w3.eth.gas_price*0.8)
                    })
                    if self.chain == 'bsc':
                        del tx['maxFeePerGas']
                        del tx['maxPriorityFeePerGas']
                        tx['gasPrice'] = self.w3.eth.gas_price
                    sign = self.account.sign_transaction(tx)
                    hash_ = self.w3.eth.send_raw_transaction(sign.rawTransaction)
                    status = self.check_status_tx(hash_)
                    self.sleep_indicator(5)
                    if status == 1:
                        logger.success(
                            f'{self.address}:{self.chain} - успешно отправил сообщение {message} в {self.to} : {self.scan}{self.w3.to_hex(hash_)}...')
                        time.sleep(5)
                        msg = self.msg(session, contract_msg, message, from_chain_id, to_chain_id,
                                       self.w3.to_hex(hash_))
                        if msg:
                            self.sleep_indicator(random.randint(self.delay[0], self.delay[1]))
                            return self.address, 'success'
                    else:
                        logger.info(f'{self.address}:{self.chain} - пробую еще раз отправлять сообщение...')
                        self.send_msg()

                except Exception as e:
                    error = str(e)
                    if 'nonce too low' in error or 'already known' in error or 'Message already executed' in error:
                        time.sleep(5)

                    elif 'INTERNAL_ERROR: insufficient funds' in error or 'insufficient funds for gas * price + value' in error:
                        logger.error(
                            f'{self.address}:{self.chain} - не хватает денег на газ, заканчиваю работу через 5 секунд...')
                        time.sleep(5)
                        return self.address, 'error'
                    else:
                        logger.error(f'{self.address}:{self.chain} - {e}...')
                        return self.address, 'error'
            else:
                logger.info(f'{self.address}:{self.chain} - cплю 30 секунд так как л0 не активен...')
                self.sleep_indicator(30)
