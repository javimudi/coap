from __future__ import with_statement
import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('coapOption')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

import coapUtils     as u
import coapException as e
import coapDefines   as d

#============================ classes =========================================

class coapOption(object):
    
    def __init__(self,optionNumber):
        
        # store params
        self.optionNumber = optionNumber
        self.length       = 0
    
    #======================== abstract methods ================================
    
    def getPayloadBytes(self):
        raise NotImplementedError()
    
    #======================== public ==========================================
    
    def toBytes(self,lastOptionNum):
        
        payload    = self.getPayloadBytes()
        delta      = self.optionNumber-lastOptionNum
        
        # optionDelta and optionDeltaExt fields
        if   delta<=12:
            optionDelta      = delta
            optionDeltaExt   = u.int2buf(    delta,0)
        elif delta<=(0xff+13):
            optionDelta      = 13
            optionDeltaExt   = u.int2buf( delta-13,1)
        elif delta<=(0xffff+269):
            optionDelta      = 14
            optionDeltaExt   = u.int2buf(delta-269,2)
        else:
            raise ValueError('delta is too large: %s' % (delta))
        
        # optionLength and optionLengthExt fields
        if   len(payload)<=12:
            optionLength     = len(payload)
            optionLengthExt  = u.int2buf(    len(payload),0)
        elif len(payload)<=(0xff+13):
            optionLength     = 13
            optionLengthExt  = u.int2buf( len(payload)-13,1)
        elif len(payload)<=(0xffff+269):
            optionLength     = 14
            optionLengthExt  = u.int2buf(len(payload)-269,2)
        else:
            raise ValueError('payload is too long, %s bytes' % (len(payload)))
        
        returnVal  = []
        returnVal += [optionDelta<<4 | optionLength]
        returnVal += optionDeltaExt
        returnVal += optionLengthExt
        returnVal += payload
        
        return returnVal

#=== OPTION_NUM_IFMATCH

#=== OPTION_NUM_URIHOST

#=== OPTION_NUM_ETAG

#=== OPTION_NUM_IFNONEMATCH

#=== OPTION_NUM_URIPORT

#=== OPTION_NUM_LOCATIONPATH

#=== OPTION_NUM_URIPATH

class UriPath(coapOption):
    
    def __init__(self,path):
        
        # initialize parent
        coapOption.__init__(self,d.OPTION_NUM_URIPATH)
        
        # store params
        self.path = path
    
    def __repr__(self):
        return 'UriPath(path=%s)' % (self.path)
    
    def getPayloadBytes(self):
        return [ord(b) for b in self.path]

#=== OPTION_NUM_CONTENTFORMAT

class ContentFormat(coapOption):
    
    def __init__(self,cformat):
        
        assert len(cformat)==1
        assert cformat[0] in d.FORMAT_ALL
        
        # initialize parent
        coapOption.__init__(self,d.OPTION_NUM_CONTENTFORMAT)
        
        # store params
        self.format = cformat[0]
    
    def __repr__(self):
        return 'ContentFormat(format=%s)' % (self.format)
    
    def getPayloadBytes(self):
	return [self.format]


#=== OPTION_NUM_MAXAGE

#=== OPTION_NUM_URIQUERY

#=== OPTION_NUM_ACCEPT

#=== OPTION_NUM_LOCATIONQUERY

#=== OPTION_NUM_BLOCK2

class Block2(coapOption):
    
    def __init__(self,num=None,m=None,szx=None,rawbytes=[]):
        
        if rawbytes:
            assert num==None
            assert m==None
            assert szx==None
        else:
            assert num!=None
            assert m!=None
            assert szx!=None
        
        # initialize parent
        coapOption.__init__(self,d.OPTION_NUM_BLOCK2)
        
        # store params
        if num:
            # values of num, m, szx specified explicitly
            self.num   = num
            self.m     = m
            self.szx   = szx
        else:
            # values of num, m, szx need to be extracted
            if   len(rawbytes)==1:
                self.num   = (rawbytes[0]>>4)&0x0f
                self.m     = (rawbytes[0]>>3)&0x01
                self.szx   = (rawbytes[0]>>0)&0x07
            elif len(rawbytes)==2:
                self.num   = rawbytes[0]<<8 | (rawbytes[1]>>4)&0x0f
                self.m     = (rawbytes[1]>>3)&0x01
                self.szx   = (rawbytes[1]>>0)&0x07
            elif len(rawbytes)==3:
                self.num   = rawbytes[0]<<16 | rawbytes[1]<<8 | (rawbytes[2]>>4)&0x0f
                self.m     = (rawbytes[2]>>3)&0x01
                self.szx   = (rawbytes[2]>>0)&0x07
            else:
                raise ValueError('unexpected Block2 len=%s' % (len(rawbytes)))
    
    def __repr__(self):
        return 'Block2(num=%S,m=%s,szx=%s)' % (self.num,self.m,self.szx)
    
    def getPayloadBytes(self):
        return NotImplementedError()

#=== OPTION_NUM_BLOCK1

#=== OPTION_NUM_PROXYURI

#=== OPTION_NUM_PROXYSCHEME

#============================ functions =======================================

def parseOption(message,previousOptionNumber):
    '''
    \brief Extract an option from the beginning of a message.
    
    \param[in] message              A list of bytes.
    \param[in] previousOptionNumber The option number from the previous option
        in the message; set to 0 if this is the first option.
    
    \return A tuple with the following elements:
        - element 0 is the option that was extracted. If no option was found
          (end of the options or end of the packet), None is returned.
        - element 1 is the message without the option.
    '''
    
    log.debug(
        'parseOption message=%s previousOptionNumber=%s' % (
            u.formatBuf(message),
            previousOptionNumber,
        )
    )
    
    #==== detect end of packet
    if len(message)==0:
        message = message[1:]
        return (None,message)
    
    #==== detect payload marker
    if message[0]==d.COAP_PAYLOAD_MARKER:
        message = message[1:]
        return (None,message)
    
    #==== parse option
    
    # header
    optionDelta  = (message[0]>>4)&0x0f
    optionLength = (message[0]>>0)&0x0f
    message = message[1:]
    
    # optionDelta
    if   optionDelta<=12:
        pass
    elif optionDelta==13:
        if len(message)<1:
            raise e.messageFormatError('message to short, %s bytes: not space for 1B optionDelta' % (len(message)))
        optionDelta = u.buf2int(message[0])+13
        message = message[1:]
    elif optionDelta==14:
        if len(message)<2:
            raise e.messageFormatError('message to short, %s bytes: not space for 2B optionDelta' % (len(message)))
        optionDelta = u.buf2int(message[0:1])+269
        message = message[2:]
    else:
        raise e.messageFormatError('invalid optionDelta=%s' % (optionDelta))
    
    log.debug('optionDelta   = %s' % (optionDelta))
    
    # optionLength
    if   optionLength<=12:
        pass
    elif optionLength==13:
        if len(message)<1:
            raise e.messageFormatError('message to short, %s bytes: not space for 1B optionLength' % (len(message)))
        optionLength = u.buf2int(message[0])+13
        message = message[1:]
    elif optionLength==14:
        if len(message)<2:
            raise e.messageFormatError('message to short, %s bytes: not space for 2B optionLength' % (len(message)))
        optionLength = u.buf2int(message[0:1])+269
        message = message[2:]
    else:
        raise e.messageFormatError('invalid optionLength=%s' % (optionLength))
    
    log.debug('optionLength  = %s' % (optionLength))
    
    # optionValue
    if len(message)<optionLength:
        raise e.messageFormatError('message to short, %s bytes: not space for optionValue' % (len(message)))
    optionValue = message[:optionLength]
    message = message[optionLength:]
    
    log.debug('optionValue   = %s' % (u.formatBuf(optionValue)))
    
    #===== create option
    optionNumber = previousOptionNumber+optionDelta
    
    log.debug('optionNumber  = %s' % (optionNumber))
    
    if optionNumber not in d.OPTION_NUM_ALL:
        raise e.messageFormatError('invalid option number %s (0x{0:x})' % (optionNumber))
    
    if   optionNumber==d.OPTION_NUM_URIPATH:
        option = UriPath(path=''.join([chr(b) for b in optionValue]))
    elif optionNumber==d.OPTION_NUM_CONTENTFORMAT:
        option = ContentFormat(cformat=optionValue)
    elif optionNumber==d.OPTION_NUM_BLOCK2:
        option = Block2(rawbytes=optionValue)
    else:
        raise NotImplementedError('option %s not implemented' % (optionNumber))
    
    return (option,message)
