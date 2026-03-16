#!/usr/bin/env python3
"""Buffer pool manager with LRU eviction for database pages."""
import sys
from collections import OrderedDict

class Page:
    def __init__(self,page_id,data=None):
        self.page_id=page_id;self.data=data or bytearray(4096)
        self.dirty=False;self.pin_count=0

class BufferPool:
    def __init__(self,capacity=10):
        self.capacity=capacity;self.pages=OrderedDict()
        self.disk={};self.hits=0;self.misses=0
    def fetch(self,page_id):
        if page_id in self.pages:
            self.pages.move_to_end(page_id);self.hits+=1
            self.pages[page_id].pin_count+=1
            return self.pages[page_id]
        self.misses+=1
        if len(self.pages)>=self.capacity:self._evict()
        data=self.disk.get(page_id,bytearray(4096))
        page=Page(page_id,bytearray(data));self.pages[page_id]=page
        page.pin_count=1;return page
    def unpin(self,page_id,dirty=False):
        if page_id in self.pages:
            self.pages[page_id].pin_count=max(0,self.pages[page_id].pin_count-1)
            if dirty:self.pages[page_id].dirty=True
    def _evict(self):
        for pid in list(self.pages.keys()):
            page=self.pages[pid]
            if page.pin_count==0:
                if page.dirty:self.disk[pid]=bytes(page.data)
                del self.pages[pid];return
        raise RuntimeError("All pages pinned!")
    def flush(self,page_id=None):
        targets=[page_id] if page_id else list(self.pages.keys())
        for pid in targets:
            if pid in self.pages and self.pages[pid].dirty:
                self.disk[pid]=bytes(self.pages[pid].data)
                self.pages[pid].dirty=False
    def hit_rate(self):
        total=self.hits+self.misses;return self.hits/total if total else 0

def main():
    if len(sys.argv)>1 and sys.argv[1]=="--test":
        bp=BufferPool(3)
        p1=bp.fetch(1);p1.data[0]=42;bp.unpin(1,dirty=True)
        p2=bp.fetch(2);bp.unpin(2)
        p3=bp.fetch(3);bp.unpin(3)
        # This should evict page 1 (LRU)
        p4=bp.fetch(4);bp.unpin(4)
        assert 1 not in bp.pages
        # Page 1 data should be on disk (was dirty)
        assert bp.disk[1][0]==42
        # Re-fetch from disk
        p1b=bp.fetch(1)
        assert p1b.data[0]==42
        bp.unpin(1)
        # Hit rate
        assert bp.misses>0
        # Pin prevents eviction
        bp2=BufferPool(2)
        p=bp2.fetch(1);bp2.fetch(2)  # both pinned
        try:bp2.fetch(3);assert False
        except RuntimeError:pass
        print("All tests passed!")
    else:
        bp=BufferPool(5)
        for i in range(10):p=bp.fetch(i);bp.unpin(i)
        print(f"Hit rate: {bp.hit_rate():.1%}")
if __name__=="__main__":main()
