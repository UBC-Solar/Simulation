import numpy as np

from matplotlib import pyplot as plt
from simulation.library.libraries import Libraries
from perlin_noise import PerlinNoise
from simulation.common.helpers import normalize


class Noise:
    def __init__(self, golang=True, lib: Libraries = None):
        self.golang = golang
        self.lib = lib
        self.noise = None
        self.randomSeed = 0

    def generate_perlin_noise(self, length, width, buffer):
        # Notably, compared to other Go implementations, the Go implementation of generate_perlin_noise and the
        # Pythonic version have rather different functionalities, but both will return results that are valid
        # for our use case despite their differences.

        if self.golang and self.lib is not None:
            self.noise = self.lib.golang_generate_perlin_noise(randomSeed=self.randomSeed)
            self.randomSeed += 1
        else:
            noise1 = PerlinNoise(octaves=3)
            noise2 = PerlinNoise(octaves=6)
            noise3 = PerlinNoise(octaves=12)
            noise4 = PerlinNoise(octaves=48)

            x, y = length * buffer, width
            noise_list = []

            for i in range(x):
                row = []
                for j in range(y):
                    noise_val = noise1([i / x, j / y])
                    noise_val += 0.5 * noise2([i / x, j / y])
                    noise_val += 0.25 * noise3([i / x, j / y])
                    noise_val += 0.125 * noise4([i / x, j / y])
                    row.append(noise_val)
                noise_list.append(row)
            self.noise = np.array(noise_list)

    def get_perlin_noise_vector(self, length, buffer=16) -> np.ndarray:
        if self.noise is None:
            self.generate_perlin_noise(length, length, buffer)
        noise = self.noise[0][:length]
        vector = np.resize(normalize(noise), (1, length))
        return vector

    def get_perlin_noise_matrix(self, length, width, buffer=16) -> np.ndarray:
        if self.noise is None:
            self.generate_perlin_noise(length, width, buffer)

        self.noise = np.resize(self.noise, (width, length))

        return self.noise

    def display_noise(self, width, length):
        pic = []
        for i in range(width):
            row = []
            for j in range(length):
                row.append(self.noise[i][j] * 256)
            pic.append(row)

        plt.imshow(pic, cmap='gray')
        plt.show()
