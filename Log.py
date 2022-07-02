import os
import io
import sys
from tkinter import Tk, messagebox
import platform

from datetime import datetime

#from HelpersPackage import MessageBox

# The idea is that Log will print the log message to the console and also to a log file. Additionally, if the iserror flag is True,
# it will print it to an errors file.
# The log file and the error file are set up using LogOpen()
# There is an additional unusual feature handy when dealing with processing of large amounts of data.
#       The problem is that when processing a large amount of data,  the errors occur too deep for the code to know the
#       line of input (or whatever) that produced the error.  One approach would be to log every line of input, but this may
#       be unacceptably clumsy.
#       To deal with this, use LogSetHeader to save a header string for each line processed.  This header string will only be
#       output to the log if a Log call is made subsequently and it will only be output once no matter how many Logs happen until a new
#       header is saved.

#=============================================================================
# If Log has not been initialized, initialize it using default log names
def LogCheck() -> None:
    try:
        g_logFile
    except NameError:
        LogOpen("Log.txt", "Log Errors.txt")


#=============================================================================
# Print the text to a log file open by the main program
# If isError is set also print it to the error file.
def Log(text: str, isError: bool=False, noNewLine: bool=False, Print=True, Clear=False, Flush=True, timestamp=False) -> None:
    global g_logFile
    global g_logFileName
    global g_logErrorFile
    global g_logErrorFileName
    global g_logHeaderPrint
    global g_logHeaderFile
    global g_logHeaderError
    global g_errorLogged         # True if anything is logged to the error log
    g_errorLogged=False

    LogCheck()

    if timestamp:
        text=f"{datetime.now():%H:%M:%S}: "+text

    # We don't actually create the log files until there's something written to them
    # LogOpen stores the names of the output files in g_logFile and g_errorFile.
    # (If those globals don't contain strings, then they were probably never initialized.)
    # Now, if the file is needed, we open the files and store the file handle in that global instead.
    if g_logFile is None and g_logFileName is not None:
        try:
            g_logFile=open(g_logFileName, "w+", encoding='utf-8')
        except Exception as e:
            MessageBox("Exception in LogOpen("+g_logFileName+")  Exception="+str(e))

    if isError and g_logErrorFile is None and g_logErrorFileName is not None:
        try:
            g_logErrorFile=open(g_logErrorFileName, "w+", buffering=1, encoding='utf-8')
        except Exception as e:
            MessageBox("Exception in LogOpen("+g_logErrorFileName+")  Exception="+str(e))

    # If Clear=True, then we clear pre-existing headers
    if Clear:
        g_logHeaderPrint=""
        g_logHeaderFile=""
        g_logHeaderError=""

    # We allow the user to specify that the file is not terminated with a new line, allowing several log calls
    # to go to the same output line.
    newlinechar="\n"
    if noNewLine:
        newlinechar=" "

    # If this is the first log entry for this header, print it and then clear it so it's not printed again
    if Print:
        if g_logHeaderPrint != "":
            print(g_logHeaderPrint)
            g_logHeaderPrint=""
    if g_logHeaderFile != "":
        print("\n"+g_logHeaderFile, file=g_logFile)
        g_logHeaderFile=""
    if isError:
        # If this is an error entry and is the first error entry for this header, print the header and then clear it so it's not printed again
        if g_logHeaderError != "":
            print("----\n"+g_logHeaderError, file=g_logErrorFile)
        g_logHeaderError=""
        g_errorLogged=True

    if g_logFile is None and g_logErrorFile is None:
        print("*** Log() called prior to call to LogOpen()", end=newlinechar)
        print("*** text="+text, end=newlinechar)

    # Print the log entry itself
    if Print:
        if text.endswith(newlinechar):
            print(text, end="") # Don't add a newline to lines already having one
        else:
            print(text, end=newlinechar)
    if g_logFile is not None and isinstance(g_logFile, io.TextIOWrapper):
        try:
            print(text, file=g_logFile, end=newlinechar)
            if Flush:
                LogFlush()
        except:
            pass
    if isError and g_logErrorFile is not None and isinstance(g_logErrorFile, io.TextIOWrapper):
        print(text, file=g_logErrorFile, end=newlinechar)
        LogFlush()  # Always flush after an error message


#=============================================================================
# Shortcut to calling Log(...isError=True) to log an error
def LogError(text: str) -> None:
    Log(text, isError=True)


#=============================================================================
# Returns True if an error has been logged since the Log was started
def LogErrorHasBeenLogged() -> bool:
    global g_errorLogged
    return g_errorLogged


#=============================================================================
# Displays the error file in a pop-up window if any errors have been logged
def LogDisplayErrorsIfAny() -> None:
    global g_logErrorFileName
    if not LogErrorHasBeenLogged():
        return

    if platform.system() == "Windows":
        os.startfile(g_logErrorFileName)
    # if platform.system() == "Darwin":   # Mac!
    #     messagebox.showinfo(title=None, message=f"An error has been logged/nLook at {g_logErrorFile} for details.")


#=============================================================================
# Set the header for any subsequent log entries
# Note that this header will only be printed once, and then only if there has been a log entry
def LogSetHeader(name: str) -> None:
    global g_logHeaderPrint
    global g_logHeaderFile
    global g_logHeaderError
    global g_logLastHeader

    LogCheck()

    # If we're setting a header which is a new header, we reset all the header variables
    if g_logLastHeader == "" or name != g_logLastHeader:
        g_logHeaderPrint=name
        g_logHeaderFile=name
        g_logHeaderError=name
        g_logLastHeader=name


#=============================================================================
# This really doesn't do the open, but just caches the filenames.  They'll be opened by Log() only if needed.
def LogOpen(logfilename: str, errorfilename: str, dated: bool=False) -> None:

    if dated:
        # If dated is True, we insert a datestring at the end of the filename
        d=datetime.now().strftime("%Y-%m-%d %H.%M.%S")
        fname, ext=os.path.splitext(logfilename)
        if ext is None or ext == "":    # If there was no extension, add .txt
            ext=".txt"
        logfilename=fname+" "+d+ext

        fname, ext=os.path.splitext(errorfilename)
        if ext is None or ext == "":
            ext=".txt"
        errorfilename=fname+" "+d+ext

    global gerrorFound
    gerrorFound=False

    global g_logFileName
    g_logFileName=logfilename
    global g_logFile
    g_logFile=None

    global g_logErrorFileName
    g_logErrorFileName=errorfilename
    global g_logErrorFile
    g_logErrorFile=None

    global g_logHeaderPrint
    g_logHeaderPrint=""
    global g_logHeaderError
    g_logHeaderError=""
    global g_logHeaderFile
    g_logHeaderFile=""
    global g_logLastHeader
    g_logLastHeader=""


#=============================================================================
def LogFlush() -> None:
    LogCheck()
    global g_logFile
    if g_logFile is not None and isinstance(g_logFile, io.TextIOWrapper):
        g_logFile.flush()
    global g_logErrorFile
    if g_logErrorFile is not None and isinstance(g_logErrorFile, io.TextIOWrapper):
        g_logErrorFile.flush()


#=============================================================================
# Needed only if you want to close the log files before program termination.
def LogClose() -> None:
    LogCheck()
    global g_logFile
    if g_logFile is not None and isinstance(g_logFile, io.TextIOWrapper):
        g_logFile.close()
    global g_logErrorFile
    if g_logErrorFile is not None and isinstance(g_logErrorFile, io.TextIOWrapper):
        g_logErrorFile.close()


#=============================================================================
# Check to see if a filename exists.  If it doesn't, log the fact and raise an exception
# If it does exiats, return doing notning.
def LogFailureAndRaiseIfMissing(fname: str) -> None:
    LogCheck()
    if not os.path.exists(fname):
        Log("Fatal error: Can't find "+fname, isError=True)
        raise FileNotFoundError


# =============================================================================
# Display a message box (needed only for the built/packaged version)
# User sparingly, since the messagebox must be closed by hand and can be annoying.
# It does nothing in the debug version
def MessageBox(s: str) -> None:
    Log(f'MessageBox({s}) called.')
    if sys.gettrace() is None:      # This is an incantation which detects the presence of a debugger
        root = Tk()
        root.withdraw()
        messagebox.showinfo(title=None, message="Finished!")
