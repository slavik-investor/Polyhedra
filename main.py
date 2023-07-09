from utils import *
from config import *


def main():
    wallets, results = [], []
    print(f'\n{" " * 32}автор - https://t.me/iliocka{" " * 32}\n')

    for key in keys:
        if proxies:
            proxy = random.choice(proxies)
        else:
            proxy = None

        if MODE in [0, 1]:

            if TYPE == 'nftbridger':
                logger.info('Запущен режим минта и бриджа нфт...')
                zk = ZkBridge(key, DELAY, chain, to, MORALIS_API_KEY, MODE, proxy)
                res = zk.claim_on_destinaton()
                wallets.append(res[0]), results.append(res[1])

        if TYPE == 'messenger':
            logger.info('Запущен режим отправки сообщений...')
            zk = ZkMessage(key, chain, to, DELAY, proxy)
            res = zk.send_msg()
            wallets.append(res[0]), results.append(res[1])

    if MODE == 2:
        if TYPE == 'claimer':
            logger.info('Запущен режим клейма нфт, которые не удалось забриджить...')
            for key, hash_ in [i.split(':') for i in hashes_]:
                if proxies:
                    proxy = random.choice(proxies)
                else:
                    proxy = None

                zk = ZkBridge(key, DELAY, chain, to, MORALIS_API_KEY, MODE, proxy)
                res = zk.redeem_nft(hash_=hash_)
                wallets.append(res[0]), results.append(res[1])
    res = {'address': wallets, 'result': results}
    df = pd.DataFrame(res)
    df.to_csv('results.csv', mode='a', index=False)
    logger.success('Минетинг закончен...')
    print(f'\n{" " * 32}автор - https://t.me/iliocka{" " * 32}\n')
    print(f'\n{" " * 32}donate - EVM 0xFD6594D11b13C6b1756E328cc13aC26742dBa868{" " * 32}\n')
    print(f'\n{" " * 32}donate - trc20 TMmL915TX2CAPkh9SgF31U4Trr32NStRBp{" " * 32}\n')


if __name__ == '__main__':
    main()
