import numpy as np

from matplotlib import pyplot as plt


class Noise:
    def __init__(self):
        self.noise_gaus = None

    def get_gauss_noise_matrix(self, length, width, buffer=16) -> np.ndarray:
        if self.noise_gaus is None:
            self.noise_gaus = np.random.normal(loc=0.0, scale=1.0, size=(length * buffer, width))

        self.noise_gaus = np.resize(self.noise_gaus, (width, length))

        return self.noise_gaus

    def display_noise(self, width, length):
        pic = []
        for i in range(width):
            row = []
            for j in range(length):
                row.append(self.noise_gaus[i][j] * 256)
            pic.append(row)

        plt.imshow(pic, cmap='gray')
        plt.show()
