// SPDX-License-Identifier: MIT
// Actual compiled loader/context and original list initializer; local stock
// required. Trust and table-only package are synthetic, never qualification.
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <map>
#include <string>
#include <vector>
#include "machine.h"
#include "mc68k/Musashi/m68k.h"
#include "mc68k/cpuState.h"
static constexpr uint32_t sp=0x46c7f920,packet=0x47010000,hash_input=0x47014000,hash_output=0x47015000,stop=0x47300000;
static std::vector<uint8_t> load(const char *path) {std::ifstream f(path,std::ios::binary);assert(f.good());return {(std::istreambuf_iterator<char>(f)),{}};}
static void put(std::vector<uint8_t>& b,unsigned at,uint32_t value) {for(unsigned i=0;i<4;i++)b[at+i]=uint8_t(value>>(24-8*i));}
struct Probe {
    ot::Machine m;std::map<std::string,uint32_t> symbols;unsigned calls=0;
    Probe(const std::vector<uint8_t>& stock,const std::vector<uint8_t>& code,const char *map):m(stock) {
        std::ifstream f(map);std::string at,type,name;while(f>>at>>type>>name)symbols[name]=std::stoul(at,nullptr,16);
        for(unsigned i=0;i<code.size();i++)m.write8(0x47400000+i,code[i]);
        for(const char *n:{"prepare","publish","restore","retire"})symbols[n]=symbols.at(std::string("modwerk_backend_")+n);
        constexpr struct {uint32_t tcb,stack;} tasks[]={
            {0x46c7fb0c,0x46c7ea20},{0x460bcc2c,0x460bc42c},{0x460d4f80,0x460d4780},
            {0x460d59d4,0x460d51d4},{0x460fab80,0x460fabd4},{0x460ffd44,0x460fdd44},
            {0x460e0e38,0x460dee38},{0x460ddde4,0x460d9de4},{0x46105508,0x4610555c},
            {0x46c7bed8,0x460d6de4},{0x46c7ae84,0x46c7aed8}};
        for(auto t:tasks){m.write32(t.tcb,0);m.write32(t.tcb+0x48,t.stack+8);}
        m.write32(0x800068fc,tasks[0].tcb);for(unsigned i=0;i<8;i++)m.write32(0x800068dc+4*i,0);
        m.write32(0x800068dc,tasks[0].tcb);m.write32(tasks[0].tcb,tasks[0].tcb);
        m.mapRegion(0x10000000,0x000b0000);m.mapRegion(0x100c0000,0x00040000);
        m.write32(0x46c82456,0x400e21e0);
        m.write32(0x400cbf4c,0);call("fixture_clear_table");
    }
    uint32_t call_at(uint32_t entry,std::vector<uint32_t> args={},uint32_t held=0) {
        auto *cpu=m.getCpuState();for(unsigned r=0;r<15;r++)m68k_set_reg(cpu,m68k_register_t(M68K_REG_D0+r),0);
        m68k_set_reg(cpu,M68K_REG_D2,held);m68k_set_reg(cpu,M68K_REG_SP,sp);m.write32(sp,stop);
        for(unsigned i=0;i<args.size();i++)m.write32(sp+4+4*i,args[i]);m.write32(sp+66,0);
        auto unmapped=m.unmappedCount();m68k_set_reg(cpu,M68K_REG_PC,entry);unsigned budget=100000000;
        while(m.pc()!=stop&&budget--)assert(m.step());
        if(m.pc()!=stop || m.unmappedCount()!=unmapped)std::fprintf(stderr,"native table call failed entry=%x pc=%x new_unmapped=%llu\n",entry,m.pc(),static_cast<unsigned long long>(m.unmappedCount()-unmapped));
        assert(m.pc()==stop && m.unmappedCount()==unmapped);calls++;return m68k_get_reg(cpu,M68K_REG_D0);
    }
    uint32_t call(const char *name,std::vector<uint32_t> args={},uint32_t held=0){return call_at(symbols.at(name),args,held);}
    std::vector<uint8_t> hash(const std::vector<uint8_t>& b) {
        for(unsigned i=0;i<b.size();i++)m.write8(hash_input+i,b[i]);call("fixture_hash",{hash_input,uint32_t(b.size()),hash_output});
        std::vector<uint8_t> digest(32);for(unsigned i=0;i<32;i++)digest[i]=m.read8(hash_output+i);return digest;
    }
    std::vector<uint8_t> stock(uint32_t at,unsigned n){std::vector<uint8_t>b(n);for(unsigned i=0;i<n;i++)b[i]=m.read8(at+i);return b;}
    std::vector<uint8_t> package(unsigned family) {
        unsigned count=family==1?3:16,insert=family==1?3:2,added=family==1?3:1;
        std::vector<uint8_t> image(512),relocs,sites,copies;
        for(unsigned t=0;t<3;t++)for(unsigned row=insert;row<insert+added;row++) {
            unsigned at=80+80*t+4*row;put(image,at,400+4*row);unsigned old=relocs.size();relocs.resize(old+4);put(relocs,old,at);
        }
        image[400]=0x4e;image[401]=0x75;
        auto addsite=[&](uint32_t at,const std::vector<uint8_t>& write,bool relocate) {
            auto before=stock(at,write.size()),digest=hash(before);unsigned start=sites.size();sites.resize(start+40+write.size()+(relocate?2:0));
            put(sites,start,at);sites[start+4]=write.size();sites[start+6]=write.size();sites[start+7]=relocate?1:0;
            for(unsigned i=0;i<32;i++)sites[start+8+i]=digest[i];for(unsigned i=0;i<write.size();i++)sites[start+40+i]=write[i];
        };
        const std::vector<std::vector<uint32_t>> refs=family==1?std::vector<std::vector<uint32_t>>{{0x40065bd8},{0x40065bde},{0x40065cc4,0x40065d3e,0x40065d58,0x40065d72}}:
            std::vector<std::vector<uint32_t>>{{0x40068efe},{0x40068f0a},{0x40069022,0x4006903e,0x40069056}};
        unsigned sitecount=0,copycount=0;const uint32_t roots[2][3]={{0x400b27d0,0x400b27dc,0x400b282c},{0x400b2a34,0x400b2a74,0x400b2ac0}};
        for(unsigned t=0;t<3;t++) {
            std::vector<uint8_t> pointer(4);put(pointer,0,80+80*t);for(uint32_t at:refs[t]){addsite(at,pointer,true);sitecount++;}
            for(unsigned first=0;first<count;) {
                unsigned end=first<insert?insert:count,n=(end-first)*4;if(n>32)n=32;
                unsigned offset=80+80*t+4*first+(first>=insert?4*added:0);auto bytes=stock(roots[family-1][t]+4*first,n),digest=hash(bytes);
                unsigned start=copies.size();copies.resize(start+44);put(copies,start,offset);put(copies,start+4,roots[family-1][t]+4*first);copies[start+9]=n;
                for(unsigned i=0;i<32;i++)copies[start+12+i]=digest[i];copycount++;first+=n/4;
            }
        }
        addsite(family==1?0x40065c7c:0x40068fb2,family==1?std::vector<uint8_t>{0x48,0x78,0,6}:std::vector<uint8_t>{0x72,0x10},false);sitecount++;
        std::vector<uint8_t> b(76);b[0]='M';b[1]='W';b[2]='R';b[3]='M';b[5]=8;put(b,8,image.size());put(b,16,relocs.size()/4);put(b,24,sitecount);put(b,28,family==1?0x7e9d5687:0x73bab3b1);
        b[50]='T';b[51]='A';b[52]='B';b[53]='L';b[54]='E';b[67]=1;put(b,68,copycount);
        b.insert(b.end(),image.begin(),image.end());b.insert(b.end(),relocs.begin(),relocs.end());b.insert(b.end(),sites.begin(),sites.end());b.insert(b.end(),copies.begin(),copies.end());return b;
    }
};
int main(int argc,char **argv) {
    assert(argc==4 || argc==5 || (argc==6 && std::string(argv[4])=="--table-packages") ||
           (argc==7 && std::string(argv[5])=="--companions"));unsigned total=0;
    if(argc==5 || argc==7) {
        struct Group {unsigned mask,offset[3],optional;std::vector<uint8_t> package;};
        std::vector<Group> groups;std::ifstream f(argv[4]);std::string path;Group g;
        while(f>>g.mask>>path>>g.offset[0]>>g.offset[1]>>g.offset[2]>>g.optional) {
            assert(g.optional<=1 && (!(g.mask&4)||!g.optional));g.package=load(path.c_str());groups.push_back(g);
        }
        assert(groups.size()==7 || groups.size()==10);unsigned transitions=0,minimumFree=262144;
        for(const auto& baseline:groups) {
            Probe p(load(argv[1]),load(argv[2]),argv[3]);auto original=load(argv[1]);
            auto write=[&](const Group& group) {for(unsigned i=0;i<group.package.size();i++)p.m.write8(packet+i,group.package[i]);};
            write(baseline);assert(p.call("prepare",{0,packet,uint32_t(baseline.package.size())})==0);
            for(const auto& group:groups) {
                write(group);p.call("fixture_review_machine",{packet,uint32_t(group.package.size()),1,1});
                p.call("fixture_review_optional_quantizer",{packet,uint32_t(group.package.size()),group.optional});
                if((group.mask&4)||group.optional)p.call("fixture_review_table_offsets",{packet,uint32_t(group.package.size()),1,1,1,group.offset[0],group.offset[1],group.offset[2]});
            }
            write(baseline);assert(p.call("prepare",{0,packet,uint32_t(baseline.package.size())})==1);
            assert(p.call("publish",{0})==1 && p.call("retire",{0})==1);
            auto baselineImage=p.call("fixture_table_image"),baselineFree=p.call("modwerk_runtime_free",{0});
            for(const auto& target:groups) {
                write(target);unsigned dropped=baseline.mask&~target.mask;
                if((baseline.mask&4)||baseline.optional||(target.mask&4)||target.optional) {
                    // Current captured register and every paused alias fence
                    // QZ acquisition and release, including same-mask variants.
                    for(uint32_t held:{0x400b27d0u,0x480b27d0u,0x40065b14u,0x48065b14u,0x40064e20u}) {
                        assert(p.call("prepare",{0,packet,uint32_t(target.package.size())},held)==0);
                        assert(p.call("fixture_table_image")==baselineImage && p.call("modwerk_runtime_free",{0})==baselineFree);
                    }
                    p.m.write32(0x460bcc2c+0x14,0x480b27d0u);
                    assert(p.call("prepare",{0,packet,uint32_t(target.package.size())})==0);p.m.write32(0x460bcc2c+0x14,0);
                    p.m.write32(0x400cbf4c,0x47060000);p.m.write32(0x400cbf40,4);
                    assert(p.call("prepare",{0,packet,uint32_t(target.package.size())})==0);p.m.write32(0x400cbf4c,0);
                }
                if(dropped) {
                    unsigned owner=dropped&1?1:dropped&2?2:4;
                    const uint8_t signature[3][3]={{'P','L',1},{'S','2',2},{'F','M',1}};unsigned row=owner==1?0:owner==2?1:2;
                    for(unsigned i=0;i<3;i++)p.m.write8(0x100a4eceu + 60+i,signature[row][i]);
                    assert(p.call("prepare",{0,packet,uint32_t(target.package.size())})==0 && p.call("fixture_table_image")==baselineImage);
                    assert(p.call("modwerk_runtime_free",{0})==baselineFree);
                    for(unsigned i=0;i<3;i++)p.m.write8(0x100a4eceu + 60+i,0);
                }
                assert(p.call("prepare",{0,packet,uint32_t(target.package.size())})==1);
                auto available=p.call("modwerk_runtime_free",{0});if(available<minimumFree)minimumFree=available;
                if(((baseline.mask|target.mask)&4)||baseline.optional||target.optional) {
                    p.m.write32(0x400cbf4c,0x47060000);p.m.write32(0x400cbf40,4);
                    assert(p.call("publish",{0})==0 && p.call("fixture_table_image")==baselineImage);p.m.write32(0x400cbf4c,0);
                }
                p.m.write32(0x460bcc2c+0x14,baselineImage+8);
                assert(p.call("publish",{0})==0 && p.call("fixture_table_image")==baselineImage);p.m.write32(0x460bcc2c+0x14,0);
                assert(p.call("publish",{0})==1);auto targetImage=p.call("fixture_table_image");
                assert(targetImage && targetImage!=baselineImage);
                for(uint32_t alias:{0u,0x08000000u}) {
                    p.m.write32(0x460bcc2c+0x14,targetImage+8-(alias?0x08000000u:0));
                    assert(p.call("restore",{0})==0 && p.call("fixture_table_image")==targetImage);
                }
                p.m.write32(0x460bcc2c+0x14,0);
                if((target.mask&~baseline.mask)&4) {
                    p.m.write8(0x100a4eceu + 0x2fd,1);
                    assert(p.call("restore",{0})==0 && p.call("fixture_table_image")==targetImage);p.m.write8(0x100a4eceu + 0x2fd,0);
                }
                assert(p.call("restore",{0})==1 && p.call("fixture_table_image")==baselineImage);
                assert(p.call("retire",{0})==1 && p.call("modwerk_runtime_free",{0})==baselineFree);transitions++;
            }
            // Removing every machine mask restores all original stock bytes
            // touched by any real package, and reclaims the entire CF arena.
            assert(p.call("prepare",{0,packet,76})==0); // truncated real package must never remove it.
            assert(p.call("modwerk_runtime_active")==1);
            std::vector<uint8_t> empty(76);empty[0]='M';empty[1]='W';empty[2]='R';empty[3]='M';empty[5]=8;
            put(empty,28,0xdb769930);for(unsigned i=0;i<empty.size();i++)p.m.write8(packet+i,empty[i]);
            assert(p.call("prepare",{0,packet,76})==1 && p.call("publish",{0})==1 && p.call("retire",{0})==1);
            assert(p.call("modwerk_runtime_active")==0 && p.call("modwerk_runtime_free",{0})==262144);
            for(const auto& group:groups) {
                auto be=[](const std::vector<uint8_t>& b,unsigned at) {return uint32_t(b[at])<<24|uint32_t(b[at+1])<<16|uint32_t(b[at+2])<<8|b[at+3];};
                unsigned at=76+be(group.package,8)+4*be(group.package,16),count=be(group.package,24);
                for(unsigned i=0;i<count;i++) {uint32_t address=be(group.package,at);unsigned n=group.package[at+4],r=group.package[at+7];
                    for(unsigned k=0;k<n;k++)assert(p.m.read8(address+k)==original[address+k-0x40000400]);at+=40+n+2*r;}
            }
            total+=p.calls;
        }
        // Raw companions (actual Repitch/Mutes/standalone QZ packets) beside each
        // group, in both install orders. `conflict` names the participants (P=1,
        // V=2, FM=4, QZ=8) whose canonical group owner holds one of its raw sites:
        // then the later prepare is refused RUNTIME_CONFLICT before any change;
        // otherwise both coexist. Table companions get exact synthetic trust.
        unsigned pairs=0,refused=0;
        if(argc==7) {
            struct Companion {unsigned conflict;std::vector<uint8_t> package;};
            std::vector<Companion> companions;std::ifstream c(argv[6]);Companion k;
            while(c>>k.conflict>>path) {assert(k.conflict && k.conflict<16);k.package=load(path.c_str());companions.push_back(k);}
            assert(!companions.empty());
            auto be=[](const std::vector<uint8_t>& b,unsigned at) {return uint32_t(b[at])<<24|uint32_t(b[at+1])<<16|uint32_t(b[at+2])<<8|b[at+3];};
            for(const auto& group:groups)for(const auto& companion:companions)for(unsigned order=0;order<2;order++) {
                Probe p(load(argv[1]),load(argv[2]),argv[3]);
                auto write=[&](const std::vector<uint8_t>& b) {for(unsigned i=0;i<b.size();i++)p.m.write8(packet+i,b[i]);};
                write(group.package);p.call("fixture_review_machine",{packet,uint32_t(group.package.size()),1,1});
                p.call("fixture_review_optional_quantizer",{packet,uint32_t(group.package.size()),group.optional});
                if((group.mask&4)||group.optional)p.call("fixture_review_table_offsets",{packet,uint32_t(group.package.size()),1,1,1,group.offset[0],group.offset[1],group.offset[2]});
                const auto& b=companion.package;uint32_t module=be(b,28);
                if(module==0x7e9d5687u || module==0x73bab3b1u) {
                    unsigned family=module==0x7e9d5687u?1:2;uint32_t offset[3]={0,0,0};
                    const uint32_t first[2][3]={{0x40065bd8,0x40065bde,0x40065cc4},{0x40068efe,0x40068f0a,0x40069022}};
                    unsigned at=76+be(b,8)+4*be(b,16),count=be(b,24);
                    for(unsigned i=0;i<count;i++) {uint32_t address=be(b,at);unsigned n=b[at+4],r=b[at+7];
                        for(unsigned t=0;t<3;t++)if(address==first[family-1][t]){assert(n==4);offset[t]=be(b,at+40);}
                        at+=40+n+2*r;}
                    assert(offset[0]&&offset[1]&&offset[2]);write(b);
                    p.call("fixture_review_table_offsets",{packet,uint32_t(b.size()),family,1,1,offset[0],offset[1],offset[2]});
                }
                unsigned owned=group.mask|((group.mask&4)||group.optional?8u:0u);bool conflict=owned&companion.conflict;
                const auto& live=order?b:group.package;const auto& later=order?group.package:b;
                write(live);assert(p.call("prepare",{0,packet,uint32_t(live.size())})==1);
                assert(p.call("publish",{0})==1 && p.call("retire",{0})==1 && p.call("modwerk_runtime_active")==1);
                auto free=p.call("modwerk_runtime_free",{0});write(later);
                if(conflict) {
                    assert(p.call("prepare",{0,packet,uint32_t(later.size())})==0 && p.call("modwerk_runtime_refusal")==3);
                    assert(p.call("modwerk_runtime_active")==1 && p.call("modwerk_runtime_free",{0})==free);refused++;
                } else {
                    assert(p.call("prepare",{0,packet,uint32_t(later.size())})==1);
                    assert(p.call("publish",{0})==1 && p.call("retire",{0})==1 && p.call("modwerk_runtime_active")==2);
                }
                pairs++;total+=p.calls;
            }
        }
        std::printf("{\"machineMasks\":7,\"packageVariants\":%u,\"transitions\":%u,\"calls\":%u,\"minimumFreeBytes\":%u,\"companionOrders\":%u,\"companionConflicts\":%u,\"pausedAliasNegatives\":true,\"retainedPartAndMenuNegatives\":true,\"sameMaskOptionalQzTransitions\":true,\"exactPreinstallRestore\":true,\"fullReclamation\":true,\"hardware\":false}\n",unsigned(groups.size()),transitions,total,minimumFree,pairs,refused);return 0;
    }
    struct ActualTable {unsigned family,offset[3];std::vector<uint8_t> package;};
    std::vector<ActualTable> actual;
    if(argc==6) {
        std::ifstream f(argv[5]);std::string path;ActualTable row;
        while(f>>row.family>>path>>row.offset[0]>>row.offset[1]>>row.offset[2]) {
            assert(row.family==1 || row.family==2);row.package=load(path.c_str());actual.push_back(row);
        }
        assert(!actual.empty()&&actual.size()<=2);
    }
    unsigned tested=0;
    for(unsigned family=1;family<=2;family++) {
        const ActualTable *selected=nullptr;
        for(const auto& row:actual)if(row.family==family){assert(!selected);selected=&row;}
        if(argc==6&&!selected)continue;
        Probe p(load(argv[1]),load(argv[2]),argv[3]);auto b=selected?selected->package:p.package(family);
        for(unsigned i=0;i<b.size();i++)p.m.write8(packet+i,b[i]);
        assert(p.call("prepare",{0,packet,uint32_t(b.size())})==0 && p.call("modwerk_runtime_active")==0);
        if(selected)p.call("fixture_review_table_offsets",{packet,uint32_t(b.size()),family,1,1,selected->offset[0],selected->offset[1],selected->offset[2]});
        else p.call("fixture_review_table",{packet,uint32_t(b.size()),family,1,1});
        auto free=p.call("modwerk_runtime_free",{0});
        const uint32_t root=family==1?0x400b27d0:0x400b2a34,consumer=family==1?0x40065b14:0x40068e00,list=family==1?0x460e43d8:0x460e4668;
        for(uint32_t held:{root,root+0x08000000,consumer,0x40064e20u}) {
            assert(p.call("prepare",{0,packet,uint32_t(b.size())},held)==0);assert(p.call("modwerk_runtime_free",{0})==free);
        }
        p.m.write32(0x400cbf4c,0x47060000);p.m.write32(0x400cbf40,family==1?4:12);
        assert(p.call("prepare",{0,packet,uint32_t(b.size())})==0);p.m.write32(0x400cbf4c,0);
        assert(p.call("prepare",{0,packet,uint32_t(b.size())})==1);
        p.m.write32(0x460bcc2c+0x14,root);assert(p.call("publish",{0})==0);p.m.write32(0x460bcc2c+0x14,0);
        // Publication refusal discards the staged candidate in normal USB
        // flow; here the actual loader can retry its still-owned candidate.
        assert(p.call("publish",{0})==1);auto image=p.call("fixture_table_image");assert(image);
        if(selected) {
            const uint32_t roots[2][3]={{0x400b27d0,0x400b27dc,0x400b282c},{0x400b2a34,0x400b2a74,0x400b2ac0}};
            unsigned count=family==1?3:16,insert=family==1?3:2,added=family==1?3:1;
            uint32_t bytes=uint32_t(b[8])<<24|uint32_t(b[9])<<16|uint32_t(b[10])<<8|b[11];
            for(unsigned table=0;table<3;table++)for(unsigned row=0;row<count+added;row++) {
                uint32_t value=p.m.read32(image+selected->offset[table]+4*row);
                if(insert<=row&&row<insert+added)assert(value>=image&&value<image+bytes);
                else assert(value==p.m.read32(roots[family-1][table]+4*(row<insert?row:row-added)));
            }
        }
        p.m.write32(0x400cbf4c,0x47060000);p.m.write32(0x400cbf40,family==1?4:12);
        assert(p.call("restore",{0})==0 && p.call("modwerk_runtime_active")==1);p.m.write32(0x400cbf4c,0);
        uint32_t alias=image>=0x48000000u?image-0x08000000u:image+0x08000000u;
        for(uint32_t ref:{image,image+8,alias,alias+8}) {p.m.write32(0x460bcc2c+0x14,ref);assert(p.call("restore",{0})==0);}
        p.m.write32(0x460bcc2c+0x14,0);
        assert(p.call("restore",{0})==1 && p.call("modwerk_runtime_active")==0);assert(p.call("retire",{0})==1);
        assert(p.call("modwerk_runtime_free",{0})==free);
        auto original=load(argv[1]);const std::vector<uint32_t> refs=family==1?std::vector<uint32_t>{0x40065bd8,0x40065bde,0x40065cc4,0x40065d3e,0x40065d58,0x40065d72,0x40065c7c}:
            std::vector<uint32_t>{0x40068efe,0x40068f0a,0x40069022,0x4006903e,0x40069056,0x40068fb2};
        for(uint32_t at:refs)for(unsigned i=0;i<(at==0x40068fb2?2u:4u);i++)assert(p.m.read8(at+i)==original[at+i-0x40000400]);
        if(selected) {
            auto be=[&](unsigned at){return uint32_t(b[at])<<24|uint32_t(b[at+1])<<16|uint32_t(b[at+2])<<8|b[at+3];};
            unsigned at=76+be(8)+4*be(16),count=be(24);
            for(unsigned i=0;i<count;i++) {uint32_t address=be(at);unsigned n=b[at+4],r=b[at+7];
                for(unsigned k=0;k<n;k++)assert(p.m.read8(address+k)==original[address+k-0x40000400]);at+=40+n+2*r;}
        }
        // The original initializer resets offset/row/cursor when a closed
        // menu reopens after Undo; no saved selection is mutated by admission.
        for(unsigned i=0;i<5;i++)p.m.write32(list+4*i,0x7fffffff);
        p.call_at(0x4007ec60,{list,family==1?3u:5u,family==1?3u:16u});
        assert(!p.m.read32(list)&&!p.m.read32(list+4)&&!p.m.read32(list+8));
        assert(p.m.read32(list+12)==(family==1?3u:5u)&&p.m.read32(list+16)==(family==1?3u:16u));total+=p.calls;tested++;
    }
    std::printf("{\"families\":%u,\"calls\":%u,\"actualPackages\":%u,\"defaultClosed\":true,\"pausedAliasAndMenuNegatives\":true,\"exactPreinstallRestore\":true,\"stockListReset\":true,\"hardware\":false}\n",tested,total,unsigned(actual.size()));
}
