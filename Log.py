import os

#=============================================================================
# Print the text to a log file open by the main program
# If isError is set also print it to the error file.
def Log(text: str, isError: bool=False, noNewLine: bool=False) -> None:
    global g_logFile
    global g_errorFile
    global g_logHeader
    global g_logErrorHeader

    newlinechar="\n"
    if noNewLine:
        newlinechar=" "

    # If this is the first log entry for this header, print it and then clear it so it's not printed again
    if g_logHeader is not None:
        print(g_logHeader)
        print("\n"+g_logHeader, file=g_logFile)
    g_logHeader=None

    if isError:
        # If this is an error entry and is the first error entry for this header, print the header and then clear it so it's not printed again
        if g_logErrorHeader is not None:
            print("----\n"+g_logErrorHeader, file=g_errorFile)
        g_logErrorHeader=None

    # Print the log entry itself
    print(text, end=newlinechar)
    print(text, file=g_logFile, end=newlinechar)
    if isError:
        print(text, file=g_errorFile, end=newlinechar)


#=============================================================================
# Set the header for any subsequent log entries
# Note that this header will only be printed once, and then only if there has been a log entry
def LogSetHeader(name: str) -> None:
    global g_logHeader
    global g_logErrorHeader
    global g_logLastHeader

    if g_logLastHeader is None or name != g_logLastHeader:
        g_logHeader=name
        g_logErrorHeader=name
        g_logLastHeader=name


#=============================================================================
def LogOpen(logfilename: str, errorfilename: str) -> None:
    global g_logFile
    g_logFile=open(logfilename, "w+")

    global g_errorFile
    g_errorFile=open(errorfilename, "w+", buffering=1)

    global g_logHeader
    g_logHeader=None
    global g_logErrorHeader
    g_logErrorHeader=None
    global g_logLastHeader
    g_logLastHeader=None


#=============================================================================
def LogClose() -> None:
    global g_logFile
    g_logFile.close()
    global g_errorFile
    g_errorFile.close()


#=============================================================================
def LogFailureAndRaiseIfMissing(fname: str) -> None:
    if not os.path.exists(fname):
        Log("Fatal error: Can't find "+fname, isError=True)
        raise FileNotFoundError
