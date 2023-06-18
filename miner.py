from rpc import BitcoinRPC
from block794700 import testBlock

import hashlib
import struct
import binascii
import time
    
class Miner():

    def __init__(self, id, config, nonceStart, nonceEnd, test=False):
        self.thread_id = id
        self.config = config
        self.nonceStart = nonceStart
        self.nonceEnd = nonceEnd
        self.test = test
        self.rpc = BitcoinRPC(self.config["core_address"], self.config["core_username"], self.config["core_password"])

    def _makeCompactSizeUint(self, inputNum):
        # Input: Integer
        # Output: String of Hex Values (prefix + little endian #)

        # Value	Bytes Used	Format
        # >= 0 && <= 252	1	uint8_t
        # >= 253 && <= 0xffff	3	0xfd followed by the number as uint16_t
        # >= 0x10000 && <= 0xffffffff	5	0xfe followed by the number as uint32_t
        # >= 0x100000000 && <= 0xffffffffffffffff	9	0xff followed by the number as uint64_t
        if inputNum <= 252:
            prefix = ""
            numberString = struct.pack("<B", inputNum).hex()
        elif inputNum <= 65535:
            prefix = "fd"
            numberString = struct.pack("<H", inputNum).hex()
        elif inputNum <= 4294967295:
            prefix = "fe"
            numberString = struct.pack("<I", inputNum).hex()
        elif inputNum <= 18446744073709551615:
            prefix = "ff"
            numberString = struct.pack("<Q", inputNum).hex()
        else:
            raise Exception("compactSize units must be <= 0xffffffffffffffff")

        return prefix + numberString

    def _doubleSHA(self, data):
        # accepts data in binary format (a bytes object) and returns it as a bytes object
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()
    
    def _reverseByteOrder(self, data):
        byteList = bytearray(data)
        byteList.reverse()
        return bytes(byteList)
    
    def _createCoinbaseTx(self, height, value, testingSolo=False):
        # RESOURCE: https://developer.bitcoin.org/reference/transactions.html
        # ---------------------------
        # |-- 32 bytes: Transaction Hash (all bits are zero)
        # |-- 4 bytes: Output Index (all bits are ones)
        # |-- 1-9bytes: Coinbase Data Size
        # |-- Variable: Coinbase Data (extra none... cool tag... something spicy)
        # |-- 4 bytes: Sequence Number (set to all ones)
        # ---------------------------
        # 01000000 .............................. Version
        # 01 .................................... Number of inputs
        # | 00000000000000000000000000000000
        # | 00000000000000000000000000000000 ...  Previous outpoint TXID
        # | ffffffff ............................ Previous outpoint index
        # |
        # | 29 .................................. Bytes in coinbase
        # | |
        # | | 03 ................................ Bytes in height
        # | | | 4e0105 .......................... Height: 328014
        # | |
        # | | 062f503253482f0472d35454085fffed
        # | | f2400000f90f54696d65202620486561
        # | | 6c74682021 ........................ Arbitrary data
        # | 00000000 ............................ Sequence

        #  01 ......................................... Number of outputs
        # | f0ca052a01000000 ......................... Satoshis (49.99990000 BTC)
        # |
        # | 19 ....................................... Bytes in pubkey script: 25
        # | | 76 ..................................... OP_DUP
        # | | a9 ..................................... OP_HASH160
        # | | 14 ..................................... Push 20 bytes as data
        # | | | cbc20a7664f2f69e5355aa427045bc15
        # | | | e7c6c772 ............................. PubKey hash
        # | | 88 ..................................... OP_EQUALVERIFY
        # | | ac ..................................... OP_CHECKSIG
        # | 00000000 ............................ Locktime

        version = self.config["transaction_version"]
        tx_in_count = "01" # just a binary 1
        output_txid = bytes.hex(struct.pack('<4Q', 0, 0, 0, 0)) # 32 bytes of 0s
        output_index = "FFFFFFFF"
        in_script_length = 4 + len(self.config["coinbase_message"])//2
        in_script_bytes = self._makeCompactSizeUint(in_script_length) # number of bytes in the opcode + height field + the message field
        # Start of the coinbase message: push first three bytes (instruction is 0x03 followed by three bytes, little endian, of height)
        push_opcode = "03"
        little_endian_height = bytes.hex(struct.pack('<I', height))[:6] #only want first three bytes
        message = self.config["coinbase_message"] # 87 bytes.
        sequence = "00000000"
        tx_out_count = "01"
        satoshis = bytes.hex(struct.pack('<q', int(value)))
        out_script_bytes = "19" # 25 bytes
        pubkey_script = "76" + "a9" + "14" + self.config["pubkey_hash"] + "88" + "ac"
        lock_time = "00000000"


        generatedTx =    version + \
                        tx_in_count + \
                            output_txid + \
                            output_index + \
                            in_script_bytes + \
                                push_opcode + \
                                little_endian_height + \
                                message + \
                            sequence + \
                        tx_out_count + \
                            satoshis + \
                            out_script_bytes + \
                            pubkey_script + \
                        lock_time

        generatedTx = generatedTx.lower()
        rawTransactionFormat = binascii.unhexlify(generatedTx) #transform the string to bytes
        coinbaseTxid = self._reverseByteOrder(self._doubleSHA(rawTransactionFormat)).hex() #hash & put into little endian format

        # add this transaction in the same format as the others... i.e. as a string (of hex values)
        coinbaseTx = {
            "data": generatedTx,
            "txid": coinbaseTxid
        }
        if self.test:
            if testingSolo:
                return coinbaseTx["data"]
            
            testCoinbaseTx = {
                "data": "0",
                "txid": testBlock["transactions"][0]["txid"]
            }
            return testCoinbaseTx
        
        return coinbaseTx
        
    def _computeMerkleRoot(self, txs):
        # input: list of transactions as json
        # output: Merkle Root for this block

        # The raw transaction format is hashed to create the transaction identifier (txid). From these txids, the merkle tree is constructed by pairing each txid with one other txid and then hashing them together. If there are an odd number of txids, the txid without a partner is hashed with a copy of itself.
        length = len(txs)
        merkleroot = txs[0]["txid"]
        
        if length == 1:
            return merkleroot # if only coinbase transaction, return just the txid of the coinbase transaction
        else:
            #txids are stored as ascii strings, so first we convert all to bytes objects
            merklehashes = [self._reverseByteOrder(binascii.unhexlify(tx["txid"])) for tx in txs]
            while len(merklehashes) > 1:
                if len(merklehashes) % 2:
                    merklehashes.append(merklehashes[-1])
                merklehashes = [self._doubleSHA(merklehashes[i] + merklehashes[i + 1]) for i in range(0, len(merklehashes), 2)]
            # revert back from little-endian (used for hashes) to big-endian
            merkleroot_le = merklehashes[0].hex()
            merkleroot_be = self._reverseByteOrder(merklehashes[0]).hex()
            return (merkleroot_le, merkleroot_be)
    
    def _computeDifficulty(self, bits):
        # Input: bits should be a hexademimal string... makes slicing & interpretting easier
        # Output: a long value for the target
        exponent = int(bits[0:2], 16) # take the first byte of the bits field as an exponent
        coefficient = int(bits[2:], 16) # the next 3 bytes are the coefficient
        ## The formula is coefficient * 2^(8*(exponent-3))
        target = coefficient * ( 2 ** (8*(exponent - (3))))
        return target

    
    def _buildBlockHeader(self):
        # A block header: 80 bytes
        # -------------------------------------------
        #|-- 4 Bytes: Version (int_32_t) little-endian
        #|-- 32 Bytes: Previous Block header hash char[32]
        #|-- 32 Bytes: Merkle Root Hash char[32]
        #|-- 4 Bytes: time unix epoch time (int_32_t) little-endian
        #|-- 4 Bytes: nBits (int_32_t) little-endian
        #|-- 4 Bytes: nonce (int_32_t) little-endian
        # -------------------------------------------

        ## TODO: Leave rpc open to interupt when new block is published so I'm not working on a stale fork
        if self.test:
            template = testBlock
        else:
            template = self.rpc.getBlockTemplate() ## call to network

        # extract information needed to build Coinbase Transaction; then build it
        height = template["height"] # the height of the block I'm working on creating
        print("Miner " + str(self.thread_id) + ": starting to mine block " + str(height) + " at " + str(time.asctime()))
        value = template["coinbasevalue"]
        coinbaseTx = self._createCoinbaseTx(height, value)

        # extract information to build the merkle root
        txs = template["transactions"]
        if not self.test:
            txs = [coinbaseTx] + txs
        numberTransactions = len(txs)
        (merkleroot_le, merkle_root_be) = self._computeMerkleRoot(txs)

        # extract information to calculate difficulty
        bits = template["bits"]
        target = self._computeDifficulty(bits)

        # build the candidate block header as a string (of hex values)
        version_le_hstr = struct.pack("<i", template["version"]).hex()
        previous_le_hstr = self._reverseByteOrder(binascii.unhexlify(template['previousblockhash'])).hex()
        curtime_le_hstr = struct.pack("<i", template["curtime"]).hex()
        bits_le_hstr = self._reverseByteOrder(binascii.unhexlify(bits)).hex()

        blockpart = version_le_hstr + \
                    previous_le_hstr + \
                    merkleroot_le + \
                    curtime_le_hstr + \
                    bits_le_hstr

        for i in range(self.nonceStart, self.nonceEnd):
            nonce = struct.pack("<I", i)
            nonceString = nonce.hex()
            candidateString = blockpart + nonceString
            candidateRaw = binascii.unhexlify(candidateString)
            candidateHashString = self._reverseByteOrder(self._doubleSHA(candidateRaw)).hex()

            candidateHashInt = int(candidateHashString, 16)

            if candidateHashInt < target :
                totalNumberTransactions = self._makeCompactSizeUint(numberTransactions)
                allTransactions = ""
                for tx in txs:
                    allTransactions += tx["data"]
                
                serializedBlock =   candidateString + \
                                    totalNumberTransactions + \
                                    allTransactions
                
                if self.test:
                    return (candidateString, serializedBlock)
                else:
                    print("Holy shit, block found!")
                    print("----- found nonce to create a hash: " + candidateHashString)
                    output = self.rpc.submitBlock(serializedBlock)
                    with open("log.txt", "a") as file:
                        file.write(nonceString + "\n")
                        file.write(candidateString + "\n")
                        file.write(candidateHashString + "\n")
                        file.write(serializedBlock + "\n")
                        file.write("Server Response: " + output + "\n")
                    print("The server responded with: " + output)
                    return (candidateString, serializedBlock)
        
        return "no solution found"
    
    def mine(self):
        print("Miner {}: spinning up...".format(self.thread_id))
        while self.rpc is None:
            print("Miner {} waiting for rpc...".format(self.thread_id))
            time.sleep(self.config["error_sleep_interval"])
        
        information = self.rpc.getMiningInfo()
        # FROM: https://developer.bitcoin.org/reference/rpc/getmininginfo.html
        # -------------------------------------------
        # |-- "blocks" : n,                (numeric) The current block
        # |-- "currentblockweight" : n,    (numeric, optional) The block weight of the last assembled block (only present if a block was ever assembled)
        # |-- "currentblocktx" : n,        (numeric, optional) The number of block transactions of the last assembled block (only present if a block was ever assembled)
        # |-- "difficulty" : n,            (numeric) The current difficulty
        # |-- "networkhashps" : n,         (numeric) The network hashes per second
        # |-- "pooledtx" : n,              (numeric) The size of the mempool
        # |-- "chain" : "str",             (string) current network name (main, test, regtest)
        # |-- "warnings" : "str"           (string) any network and blockchain warnings
        # -------------------------------------------
        while information is None:
            print("Error with connection to Bitcoin Core: 'getmininginfo' rpc failed.")
            time.sleep(self.config["error_sleep_interval"])

        while True:
            self._buildBlockHeader()
