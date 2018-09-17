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

#include <list>
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

    class HPclass {
    public:
        HPclass(): i(33), b(true), f(42.42), d(-42.42), c('f'), charp("hello world"), cp(NULL) { }
        __attribute__ ((noinline)) int donotoptim() { return noinline(i); }

        int i;
        bool b;
        float f;
        double d;
        char c;
        const char* charp;
        HPclass* cp;
    };

    class HPclass_ref {
    public:
        HPclass_ref(HPclass& ref): ref(ref) { }
        __attribute__ ((noinline)) int donotoptim() { return noinline(ref.i); }
        HPclass& ref;
    };

    struct HPclass_deriv: public HPclass {
        int i_deriv;
        float f_deriv;
    };

    struct HPclass_deriv2: public HPclass_deriv {
    };

}

bool have_cpp11;

// global class
HPclass hp_gc;

// class ptr
HPclass hp_gcp;
HPclass hp_gcp2;

// class ptr loop
HPclass hp_gcpl;
HPclass hp_gcpl2;

// global vector
vector<int> hp_gvi;

// global vector of classes
vector<HPclass> hp_gvc;

// global list of ints
list<int> hp_gli;

// global string
const string hp_gstr("bye");
string hp_gstr_long("The quick brown fox jumps over the lazy dog multiple times to do this string longer...");

// array
unsigned short hp_gaus[8] = { 4, 3, 2, 1, 8, 7, 6, 5 };
unsigned long long hp_gaaul[2][3] = { { 1, 2, 3 }, { 999999999999, 888888888888, 777777777777 } };

// union
union HPunion {
    int i;
    float f;
    const char* charp;
} hp_gunion;

// enum
enum HPenum { HP_0, HP_1, HP_100 = 100 } hp_genum = HP_100;

// reference
HPclass_ref hp_gcr(hp_gc);

// inheritance
HPclass_deriv2 hp_gcd;

// c++11
#ifdef CPP11

// global unordered map/set int to int
unordered_map<int, int> hp_gumii;
unordered_set<int> hp_gusi;

// global unique ptr
unique_ptr<int> hp_gupi;
unique_ptr<HPclass> hp_gupc;
unique_ptr<HPclass> hp_gupc_null;

// global shared ptr
shared_ptr<int> hp_gspi;
shared_ptr<HPclass> hp_gspc;
shared_ptr<HPclass> hp_gspc_null;

// thread
volatile bool hp_thread_finish;
volatile bool hp_thread_in;
mutex hp_thread_mutex;
void hp_thread_func() {
    hp_thread_mutex.lock();
    HPclass hp_tc;
    hp_tc.charp = NULL;
    hp_tc.donotoptim();
    while (!hp_thread_finish) {
        hp_thread_in = true;
        this_thread::sleep_for(chrono::milliseconds(1));
    }
    hp_thread_mutex.unlock();
}

// function
function<void ()> hp_gfunc(hp_thread_func);

#endif

int main(int argc, char** argv) {
    have_cpp11 = false;
    noinline(have_cpp11);

    // local class
    HPclass hp_lc;
    hp_lc.donotoptim();

    // global class
    hp_gc.donotoptim();

    // class ptr
    hp_gcp.donotoptim();
    hp_gcp.cp = &hp_gcp2;
    hp_gcp.charp = "top";
    hp_gcp2.charp = "bottom";

    // class ptr loop
    hp_gcpl.donotoptim();
    hp_gcpl.cp = &hp_gcpl2;
    hp_gcpl2.cp = &hp_gcpl;
    hp_gcpl.charp = "class A";
    hp_gcpl2.charp = "class B";

    // global vector
    hp_gvi.push_back(1);
    hp_gvi.push_back(7);
    hp_gvi.push_back(-100);

    // global vector of classes
    hp_gvc.resize(2);
    hp_gvc[0].i = 999;
    hp_gvc[1].i = 1001;

    // global list of ints
    hp_gli.push_back(7);
    hp_gli.push_front(49);

    // global array
    noinline(hp_gaus[5]);

    // reference
    hp_gcr.donotoptim();

    // inheritance
    hp_gcd.donotoptim();

#ifdef CPP11
    have_cpp11 = true;
    noinline(have_cpp11);

    // global unordered map/set int to int
    hp_gumii[99] = -99;
    hp_gumii[999] = -999;
    hp_gumii[9999] = -9999;
    hp_gusi.insert(-9);
    hp_gusi.insert(-91);

    // global unique ptr
    hp_gupi.reset(new int(66));
    hp_gupc.reset(new HPclass);

    // global shared ptr
    hp_gspi.reset(new int(66));
    hp_gspc.reset(new HPclass);

    // thread
    thread hp_thread(hp_thread_func);
    while (!hp_thread_in) this_thread::sleep_for(chrono::milliseconds(1)); // wait for thread
#endif

    // wait for gdb inspection and exit
    sync_gdb();

#ifdef CPP11
    hp_thread_finish = true;
    hp_thread.join();
#endif
    return 0;
}
