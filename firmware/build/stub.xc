#include <platform.h>
int g0, g1;
int f(int x){ return x*3+1; }
int main(){ par { on tile[0]: { g0 = f(1); while(1); } on tile[1]: { g1 = f(2); while(1); } } return 0; }
