"""Pinned resident DSP templates and full-payload native proofs; no stock bytes exported."""
import argparse,contextlib,dataclasses,hashlib,importlib,io,json,os,pathlib,re,shutil,subprocess,sys,tempfile
def digest(words):return hashlib.sha256(b''.join(w.to_bytes(3,'big') for w in words)).hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('worktree',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--app',type=pathlib.Path,required=True)
    a=p.parse_args();root=a.worktree.resolve();app=a.app.resolve();dest=a.output.resolve()
    rev=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if rev!=json.loads((app/'src/catalog/native-metadata.json').read_text())['revision']:p.error('Use the catalog-pinned native worktree.')
    if subprocess.run(['git','-C',str(root),'diff','--quiet','HEAD']).returncode:p.error('Native tracked sources must be clean.')
    stock=(root/'out/raw/section_3_MAIN_OS.bin').read_bytes();stockmeta=json.loads((app/'src/engine/assets/stock-dsp-metadata.json').read_text())
    if sha(stock)!=stockmeta['sourceSha256']:p.error('The original OS fingerprint is invalid.')
    os.chdir(root);sys.path[:0]=[str(root/'tools/build'),str(root/'tools')]
    os.environ.update(REMIX='miniverb',XBUS='1',SPEC='1',DEV='0',NOROUNDTRIP='0',OCTABAM_STATIC_STOCK='0',OCTABAM_NO_CACHE='1',BUILD='79')
    import toolpath,build_bus as native,dsp_modmap as dm
    dm.IMG=root/'out/raw/section_3_MAIN_OS.bin'
    from remix import registry,stock as stock_module
    from remix.schema import Remix
    known=registry.modules();char=known['CHARACTER'];text=(root/char.dsp.asm).read_text()
    text=re.sub(r'\$9([0-9a-f]{2})\b',lambda m:'$%x'%(0x36000+int(m[1],16)),text)
    if any(mark in text for mark in ['.include','.incbin','; ROTLATCH','; XBUS_GATE']):raise ValueError('Review resident source profile before exporting.')
    words,rel,init,proc=native._package(char.key,text,tuple(char.dsp.ptable))
    character={'id':char.name,'key':char.key,'author':char.author,'fxId':char.menu.fx2_id,'mode':'resident','xbusBase':0x36000,'ptableMemory':'P','words':len(words),'code':b''.join(w.to_bytes(3,'big') for w in words).hex(),'sha256':digest(words),'relocations':rel,'init':init,'proc':proc,'sources':{path:sha((root/path).read_bytes()) for path in [char.dsp.asm,'modules/character/manifest.py']},'proofs':[]}
    for base in [0x1000,0x1400,0x1801,0x2407]:
        fresh,_=native.assemble_syms(text.replace('$fab1e0',f'${base:x}'),base+len(char.dsp.ptable),label=char.key)
        character['proofs'].append({'base':base,'sha256':digest(list(char.dsp.ptable)+fresh)})
    receiverSource='modules/dsp-dynload-transport/receiver_runtime.asm';receiver=(root/receiverSource).read_text()
    variants=[];descriptors=[]
    for module in known.values():
        if module.name not in ['spectrum','modulation','character','miniverb','tapeecho','euclid']:continue
        donor=module.menu.donor_desc+0x38;ints=[];texts=[]
        def integer(offset,width,value):ints.append({'offset':offset,'width':width,'value':value})
        def string(offset,width,value):texts.append({'offset':offset,'width':width,'value':value.decode('latin1')})
        integer(native.P_ID_BYTE,1,module.menu.fx2_id);string(native.P_ABBR,5,module.menu.abbr)
        string(native.P_FULLNAME,13,module.menu.fullname+(b'79' if module.menu.build_tag else b''))
        for i,param in enumerate(module.params):
            if param.name is not None:string(native.P_PARAM_NAMES+i*6,6,param.name)
            if param.default is not None:integer(native.P_DEFAULTS+i,1,param.default)
        if module.stepped_slots:
            for i in range(12):integer(0xca+i*4,4,0);integer(0xfa+i*4,4,0)
            for i in module.stepped_slots:
                integer(0xca+i*4,4,0x4003c718);integer(0xfa+i*4,4,0x40047254 if module.params[i].count is not None and module.params[i].count<=5 else 0);integer(0x12a+i*4,4,0)
        else:
            for i in module.plain_slots:integer(0xca+i*4,4,0);integer(0xfa+i*4,4,0)
        for i in module.bipolar_slots:
            integer(0xca+i*4,4,0x4003c7a0);integer(0xfa+i*4,4,0);integer(0x12a+i*4,4,0x400328e4)
        for i,param in enumerate(module.params):
            if param.count is not None:integer(0x9a+i*4,4,param.count);integer(0x6a+i*4,4,0)
        lo,hi=native.penable(module.active_params,module.linked_params)
        integer(native.P_PENABLE_LO,4,lo);integer(native.P_PENABLE_HI,4,hi)
        slot=native.FX2_IDS+module.menu.fx2_id*4
        descriptors.append({'id':module.name,'key':module.key,'author':module.author,'fxId':module.menu.fx2_id,'donorAddress':donor,'donorSha256':sha(stock[donor-dm.BASE:donor-dm.BASE+native.DESC_LEN]),'fx2Slot':slot,'slotSha256':sha(stock[slot-dm.BASE:slot-dm.BASE+4]),'integers':ints,'strings':texts,'sourceSha256':sha((root/f'modules/{module.name}/manifest.py').read_bytes())})
    def local_words(payload,space,address,count):
        records,blob=dm.modules(stock,dm.BASE+payload['sourceOffset'],payload['bytes']);out=[]
        for at in range(address,address+count):
            record=next((r for r in records if r[0]==space and r[1]<=at<r[1]+r[2]),None)
            if record is None:raise ValueError('Stock DSP span is missing.')
            off=record[3]+(at-record[1])*3;out.append(int.from_bytes(blob[off:off+3],'little'))
        return out
    for payload in stockmeta['payloads']:
        core=payload['core'];tag=payload['tag'];null=native.PP[tag]['nul_i']
        curve=stock_module.curve_bank_record(stock,tag)
        if not curve or 'DJ EQ' not in stock_module.curve_bank_readers().get(tag,()):raise ValueError('This profile needs the native kept-DJ-EQ P-table decision.')
        for hasCharacter in [False,True]:
            table=payload['sharedEnd']+(len(words) if hasCharacter else 0)
            probe,_=native.assemble_syms(receiver.replace('@DLWORDS@','0').replace('$fab1e0',f'${table:x}'),table,label='DSP DYNLOAD STOCK')
            arena=payload['effectEnd']-table-len(probe);codeAddress=table+arena
            if arena<1131:raise ValueError('The receiver arena does not fit the largest stock package.')
            code,syms=native.assemble_syms(receiver.replace('@DLWORDS@',str(arena)).replace('$fab1e0',f'${table:x}'),codeAddress,label='DSP DYNLOAD STOCK')
            if len(code)!=len(probe) or codeAddress+len(code)!=payload['effectEnd']:raise ValueError('Receiver geometry drift.')
            copyOffset=syms['dlstubinit']-codeAddress;copyWords=code[copyOffset:]
            source=local_words(payload,0,null,len(copyWords));adjustments=[]
            for i,(old,new) in enumerate(zip(source,copyWords)):
                delta=((new-old+0x800000)&0xffffff)-0x800000
                if delta:
                    if abs(delta)>0x10000:raise ValueError('Stock stub transformation is not an address adjustment.')
                    adjustments.append({'offset':i,'delta':delta})
            masked=list(code);masked[copyOffset:]=[0]*len(copyWords)
            hook=0x8e if core==0 else 0x76;hookWords=local_words(payload,0,hook,2)
            variants.append({'core':core,'tag':tag,'hasCharacter':hasCharacter,'tableAddress':table,'tableWords':arena,'codeAddress':codeAddress,'words':len(code),'code':b''.join(w.to_bytes(3,'big') for w in masked).hex(),'sha256':digest(masked),'completeSha256':digest(code),'frame':syms['frame'],'hook':{'address':hook,'sha256':digest(hookWords)},'nullInit':null,'nullProc':null+1,'stockCopy':{'sourceAddress':null,'words':len(copyWords),'destinationOffset':copyOffset,'sourceSha256':digest(source),'sha256':digest(copyWords),'adjustments':adjustments}})
    if native._SCRATCH is not None:shutil.rmtree(native._SCRATCH,ignore_errors=True)
    # Run the unmodified native composition function in disposable output trees.
    # This is an image-byte oracle, never an emulator, render or stress gate.
    selections=[[],['character'],['spectrum','modulation','miniverb','tapeecho','euclid'],['spectrum','modulation','character','miniverb','tapeecho','euclid','repitch']]
    order=['spectrum','modulation','character','miniverb','tapeecho','euclid','repitch'];byid={m.name:m for m in known.values()};proofs=[]
    originalRemix=registry.remix
    try:
        for ids in selections:
            remix=registry.with_platform(Remix(name='octamod-resident-proof',doc='Disposable local byte oracle; never flashed.',modules=tuple(byid[id].key for id in order if id in ids),fallback='NONE'),known)
            registry.remix=lambda _:remix
            with tempfile.TemporaryDirectory(prefix='octamod-dsp-proof.') as tmp:
                work=pathlib.Path(tmp)
                for name in ['modules','dsp','vendor']:os.symlink(root/name,work/name,target_is_directory=True)
                (work/'out').mkdir();os.chdir(work)
                sys.modules.pop('build_bus',None);build=importlib.import_module('build_bus');build.IMG=root/'out/raw/section_3_MAIN_OS.bin';build.OUT=work/'out/image.bin'
                log=io.StringIO()
                try:
                    baseline=[]
                    line=next(i for i,l in enumerate((root/'tools/build/build_bus.py').read_text().splitlines(),1) if l.strip()=='import shutil, tempfile')
                    def trace(frame,event,arg):
                        if frame.f_code==build.main.__code__ and event=='line' and frame.f_lineno==line:
                            img=frame.f_locals['img']
                            for key,address in frame.f_locals['clone_addr'].items():
                                if known[key].is_stock:continue
                                baseline.append({'id':known[key].name,'address':address,'sha256':sha(img[address-dm.BASE:address-dm.BASE+build.DESC_LEN])})
                        return trace
                    try:
                        sys.settrace(trace)
                        with contextlib.redirect_stdout(log):build.main()
                    finally:sys.settrace(None)
                    image=build.OUT.read_bytes();payloads=[]
                    for payload in stockmeta['payloads']:
                        blob=image[payload['sourceOffset']:payload['sourceOffset']+payload['bytes']]
                        payloads.append({'tag':payload['tag'],'bytes':len(blob),'sha256':sha(blob)})
                    proofs.append({'moduleIds':ids,'payloads':payloads,'baselineDescriptors':baseline})
                except BaseException:
                    print(log.getvalue()[-8000:]);raise
                finally:
                    if build._SCRATCH is not None:shutil.rmtree(build._SCRATCH,ignore_errors=True)
                    os.chdir(root)
    finally:registry.remix=originalRemix
    result={'schema':1,'revision':rev,'license':'/licenses/octabam.txt','sourceSha256':stockmeta['sourceSha256'],'receiverSource':receiverSource,'receiverSourceSha256':sha((root/receiverSource).read_bytes()),'character':character,'variants':variants,'customIds':sorted({m.menu.fx2_id for m in known.values() if m.menu is not None and not m.is_stock and not m.menu.replaces}),'proofs':proofs}
    dest.write_text(json.dumps(result,indent=2)+'\n')
    (dest.parent/'descriptor-recipes.json').write_text(json.dumps({'schema':1,'revision':rev,'buildTag':'79','sourceSha256':stockmeta['sourceSha256'],'cloneBase':native.CLONE_BASE,'cloneStride':native.CLONE_STRIDE,'descriptorBytes':native.DESC_LEN,'cloneZeroSha256':sha(bytes(native.DESC_LEN)),'safeCeiling':native.SAFE_CAVE_CEIL,'recipes':descriptors},indent=2)+'\n')
    print(f'Character: {len(words)} own words, four-origin proof. Four masked receiver variants, four full native two-core payload proofs; no stock code exported or emulator gates run.')
if __name__=='__main__':main()
