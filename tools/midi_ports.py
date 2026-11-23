import ctypes, ctypes.wintypes as wt
w=ctypes.WinDLL('winmm')
class MIC(ctypes.Structure): _fields_=[('wMid',wt.WORD),('wPid',wt.WORD),('ver',wt.DWORD),('name',wt.WCHAR*32),('sup',wt.DWORD)]
def ins():
    r=[]
    for i in range(w.midiInGetNumDevs()):
        c=MIC(); w.midiInGetDevCapsW(i,ctypes.byref(c),ctypes.sizeof(c)); r.append((i,c.name))
    return r
if __name__=='__main__': print(ins())
