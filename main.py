from multiprocessing import Process
import time

from configuration import configuration
from miner import Miner

def startNewMiner(idNum, config):
    maxNonce = (2**32)-1 # 32 bits of Nonce data: 0000s through 1111s
    numberTotalThreads = config["number_threads"]
    oneSection = maxNonce // numberTotalThreads
    nonceStart = idNum * oneSection
    nonceEnd = (idNum+1) * oneSection
    idString = str(idNum)
    if len(idString) == 1:
        idString = "0" + idString
    newMiner = Miner(idString, config, nonceStart, nonceEnd, False)
    newMiner.mine()


if __name__ == '__main__':

    threads = []
    for thread_id in range(0, configuration["number_threads"]):
        process = Process(target=startNewMiner, args=(thread_id, configuration))
        process.start()
        threads.append(process)
        time.sleep(configuration["thread_delay_time"])

    # The thread will only join with the parent once it has finished (i.e. is killed)
    for thread in threads:
        thread.join()
    
    print("Miner Stopping: " + time.asctime())