/*  -*- mode: c++; coding: utf-8; c-file-style: "stroustrup"; -*-

    Copyright 2018 Asier Aguirre <asier.aguirre@gmail.com>
    This file is part of memory-tools.

    memory-tools is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    memory-tools is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with memory-tools. If not, see <http://www.gnu.org/licenses/>.

*/

#if __cplusplus >= 201103L
# define CPP11
#endif

#include <map>
#include <set>
#include <list>
#include <deque>
#include <vector>
#include <string>
#include <iostream>
#include <unistd.h>

#ifdef CPP11
#include <mutex>
#include <memory>
#include <thread>
#include <chrono>
#include <functional>
#include <unordered_map>
#include <unordered_set>
#endif

using namespace std;

namespace {

    template <typename T>
    __attribute__ ((noinline)) T noinline(const T& t) {
        volatile T c(t);
        return c;
    }

    void sync_gdb() {
        cout << "ready";
        cout.flush();
        close(STDOUT_FILENO);
        string str;
        cin >> str;
    }

    class MTclass {
    public:
        MTclass(): i(33), b(true), f(42.42), d(-42.42), c('f'), charp("hello world"), cp(NULL) { }
        __attribute__ ((noinline)) int donotoptim() { return noinline(i); }

        int i;
        bool b;
        float f;
        double d;
        char c;
        const char* charp;
        MTclass* cp;
    };

    class MTclass_ref {
    public:
        MTclass_ref(MTclass& ref): ref(ref) { }
        __attribute__ ((noinline)) int donotoptim() { return noinline(ref.i); }
        MTclass& ref;
    };

    struct MTclass_deriv: public MTclass {
        int i_deriv;
        float f_deriv;
    };

    struct MTclass_deriv2: public MTclass_deriv {
    };

}

bool have_cpp11;

// global class
MTclass mt_gc;

// class ptr
MTclass mt_gcp;
MTclass mt_gcp2;

// class ptr loop
MTclass mt_gcpl;
MTclass mt_gcpl2;

// global vector
vector<int> mt_gvi;

// global vector of classes
vector<MTclass> mt_gvc;

// global list of ints
list<int> mt_gli;

// global string
const string mt_gstr("bye");
string mt_gstr_long("The quick brown fox jumps over the lazy dog multiple times to do this string longer...");
string mt_gstr_empty;

// array
unsigned short mt_gaus[8] = { 4, 3, 2, 1, 8, 7, 6, 5 };
unsigned long long mt_gaaul[2][3] = { { 1, 2, 3 }, { 999999999999, 888888888888, 777777777777 } };

// union
union MTunion {
    int i;
    float f;
    const char* charp;
} mt_gunion;

// enum
enum MTenum { MT_0, MT_1, MT_100 = 100 } mt_genum = MT_100;

// reference
MTclass_ref mt_gcr(mt_gc);

// inheritance
MTclass_deriv2 mt_gcd;

// void
void* mt_vp(NULL);
void** mt_vpp(&mt_vp);
void*** mt_vppp(&mt_vpp);

// deque
deque<int> mt_gdequei;

// map/set ints
map<int, int> mt_gmii;
set<int> mt_gsi;

// c++11
#ifdef CPP11

// global unordered map/set int to int
unordered_map<int, int> mt_gumii;
unordered_set<int> mt_gusi;

// global unique ptr
unique_ptr<int> mt_gupi;
unique_ptr<MTclass> mt_gupc;
unique_ptr<MTclass> mt_gupc_null;

// global shared ptr
shared_ptr<int> mt_gspi;
shared_ptr<MTclass> mt_gspc;
shared_ptr<MTclass> mt_gspc_null;

// thread
volatile bool mt_thread_finish;
volatile bool mt_thread_in;
mutex mt_thread_mutex;
void mt_thread_func() {
    // static
    int mt_stvi = 4500;
    noinline(mt_stvi);

    mt_thread_mutex.lock();
    MTclass mt_tc;
    mt_tc.charp = NULL;
    mt_tc.donotoptim();
    while (!mt_thread_finish) {
        mt_thread_in = true;
        this_thread::sleep_for(chrono::milliseconds(1));
    }
    mt_thread_mutex.unlock();
}

// function
function<void ()> mt_gfunc(mt_thread_func);

#endif

int main(int argc, char** argv) {
    have_cpp11 = false;
    noinline(have_cpp11);

    // local class
    MTclass mt_lc;
    mt_lc.donotoptim();

    // global class
    mt_gc.donotoptim();

    // class ptr
    mt_gcp.donotoptim();
    mt_gcp.cp = &mt_gcp2;
    mt_gcp.charp = "top";
    mt_gcp2.charp = "bottom";

    // class ptr loop
    mt_gcpl.donotoptim();
    mt_gcpl.cp = &mt_gcpl2;
    mt_gcpl2.cp = &mt_gcpl;
    mt_gcpl.charp = "class A";
    mt_gcpl2.charp = "class B";

    // global vector
    mt_gvi.push_back(1);
    mt_gvi.push_back(7);
    mt_gvi.push_back(-100);

    // global vector of classes
    mt_gvc.resize(2);
    mt_gvc[0].i = 999;
    mt_gvc[1].i = 1001;

    // global list of ints
    mt_gli.push_back(7);
    mt_gli.push_front(49);

    // global array
    noinline(mt_gaus[5]);

    // reference
    mt_gcr.donotoptim();

    // inheritance
    mt_gcd.donotoptim();

    // deque
    mt_gdequei.push_back(33);
    mt_gdequei.push_front(32);
    mt_gdequei.push_back(44);
    mt_gdequei.push_front(-44);

    // map/set ints
    for (int k = 7; k < 13; k++) {
        mt_gmii[k] = k * 2;
        mt_gsi.insert(k);
    }

    // static
    int mt_slvi = 4499;
    noinline(mt_slvi);

#ifdef CPP11
    have_cpp11 = true;
    noinline(have_cpp11);

    // global unordered map/set int to int
    mt_gumii[99] = -99;
    mt_gumii[999] = -999;
    mt_gumii[9999] = -9999;
    mt_gusi.insert(-9);
    mt_gusi.insert(-91);

    // global unique ptr
    mt_gupi.reset(new int(66));
    mt_gupc.reset(new MTclass);

    // global shared ptr
    mt_gspi.reset(new int(66));
    mt_gspc.reset(new MTclass);

    // thread
    thread mt_thread(mt_thread_func);
    while (!mt_thread_in) this_thread::sleep_for(chrono::milliseconds(1)); // wait for thread
#endif

    // wait for gdb inspection and exit
    sync_gdb();

#ifdef CPP11
    mt_thread_finish = true;
    mt_thread.join();
#endif
    return 0;
}
