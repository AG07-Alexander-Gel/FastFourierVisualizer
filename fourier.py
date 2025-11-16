import math
import cmath

def time_domain(x) -> complex :
    return cmath.sin(9*cmath.pi*x)+cmath.sin(2*cmath.pi*x)+cmath.sin(3*cmath.pi*x)

def prin_time_domain(x):
    print(time_domain(x))

def print_values():
    for i in range(0,100):
        print(time_domain(i))

def distance(compl : complex):
    return math.sqrt(compl.real * compl.real + compl.imag*compl.imag)

def fourier():
    i = 1j
    for f in range(0,201):
        freq_test : complex = 0 + 0j
        x : float = 0.0
        while x <= 20:
            freq_test += time_domain(x) * cmath.exp(-2*cmath.pi*i*f*x)
            x+=0.05

        print(f"Frequency - {f}\t =\t {abs(freq_test)}")

fourier()
