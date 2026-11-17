// unpredictable workload: branch-heavy code with data-dependent branches.
// todo(jacob): implement. check the disassembly to make sure the compiler
// keeps real branches instead of branchless code.

#include <stdio.h>

int
main(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    return 0;
}
