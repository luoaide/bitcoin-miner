from multiprocessing import Process
import time
import binascii
import hashlib

from configuration import CONFIGURATION as config
from miner import Miner
from block794700 import testBlock

if __name__ == '__main__':
    testMiner = Miner("Test Miner", config, 3697889648, 3697889649, test=True)

    print("Performing tests...")

    # Test compactSize uint Calculation
    compactUint1 = testMiner._makeCompactSizeUint(250)
    expectedCompactUint1 = "fa"
    compactUint2 = testMiner._makeCompactSizeUint(515)
    expectedCompactUint2 = "fd0302"
    compactUint3 = testMiner._makeCompactSizeUint(4294967290)
    expectedCompactUint3 = "fefaffffff"
    compactUint4 = testMiner._makeCompactSizeUint(4294967298)
    expectedCompactUint4 = "ff0200000001000000"
    if compactUint1 == expectedCompactUint1 and compactUint2 == expectedCompactUint2 and compactUint3 == expectedCompactUint3 and compactUint4 == expectedCompactUint4:
        print("(+) passed compactSize uint Production Test")
    else:
        print("(-) failed compactSize uint Production Test")

    # Test Merkle Root Calculation
    transactions = testBlock["transactions"]
    (le_version, calculatedMerkle) = testMiner._computeMerkleRoot(transactions)
    expectedMerkle = testBlock["merkleroot"]
    if calculatedMerkle == expectedMerkle:
        print("(+) passed Merkle Root Calculation Test")
    else:
        print("(-) failed Merkle Root Calculation Test")

    # Test Block Header Construction
    expectedHeader = testBlock["header"]
    (computedBlockHeader, ignore) = testMiner._buildBlockHeader()
    if expectedHeader == computedBlockHeader:
        print("(+) passed Block Header Construction Test")
    else:
        print("(-) failed Block Header Construction Test")

    # Test Full Block Construction
    expectedFullBlock = testBlock["fullBlockHexString"]
    (ignore, computedFullBlock) = testMiner._buildBlockHeader()
    if expectedFullBlock == computedFullBlock:
        print("(+) passed Full Block Construction Test")
    else:
        print("(-) failed Full Block Construction Test")

    # Attempting to Submit a Block
    # submitBlockOutput = testMiner.rpc.submitBlock(testBlock["fullBlockHexString"])
    # expectedOutput = "duplicate"
    # print(submitBlockOutput)


    # This is the raw transcation format of my example coinbase transaction
    # data = binascii.unhexlify("020000000001010000000000000000000000000000000000000000000000000000000000000000ffffffff310343200c04f2058d642f466f756e6472792055534120506f6f6c202364726f70676f6c642f257e62175001000000000000ffffffff0254e3d1270000000016001435f6de260c9f3bdee47524c473a6016c0c055cb90000000000000000266a24aa21a9ed803e17b205cc7287a79e24ec27b9337936519d264a42626cc9a5b23fbb32a9c60120000000000000000000000000000000000000000000000000000000000000000000000000")
    # txid = "4fa59dd1178b96cc258eea2f2991422670a6c634b325e948dd2fe0f77f1e34fd"
    # # The raw format that I have includes the witness data (which is not the format used to hash & create the txid... that explains the extra 0x0001 up front and the trailing 0s)
    # block_hash = "00000000000000000000c67510c8d591028658f404bffe005354540312411ae1"
    # expected_hash = "0fd58f91047cbb81996ba8d29b1a998cc4698c1d4544b306f55cea9f25e68eba" #little endian
    # print(hashlib.sha256(hashlib.sha256(data).digest()).digest())
    
