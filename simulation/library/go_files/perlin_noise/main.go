package main

import "C"
import (
	"github.com/dgravesa/go-parallel/parallel"
	"unsafe"
)
import (
	_ "image/jpeg"
)

// GOARCH=arm64 GOOS=darwin CGO_ENABLED=1 go build -o perlin_noise.so -buildmode=c-shared main.go vector.go perlinNoise.go simplexNoise.go debug.go

//export generatePerlinNoise
func generatePerlinNoise(resultPtr *float32,
	persistence float32,
	numLayers int32,
	roughness float32,
	baseRoughness float32,
	strength float32,
	randomSeed uint32) {
	defer duration(track("generatePerlinNoise"))

	settings := &NoiseSettings{
		strength:      strength,
		baseRoughness: baseRoughness,
		roughness:     roughness,
		centre:        v3Zero,
		numLayers:     numLayers,
		persistence:   persistence,
	}

	noise := generateSimplexNoise(randomSeed)

	result := unsafe.Slice(resultPtr, 256*256)

	parallel.For(256, func(i, _ int) {
		parallel.For(256, func(j, _ int) {
			noiseValue := evaluatePerlinNoise(v3{float32(i) / 256.0, float32(j) / 256.0, 0}, noise, settings)
			result[(i*256)+j] = noiseValue
		})
	})
}

func evaluatePerlin(noise *Noise, noiseSettings *NoiseSettings) [256][256]uint8 {
	defer duration(track("evaluatePerlin"))
	var twoDArray [256][256]uint8

	parallel.For(256, func(i, _ int) {
		parallel.For(256, func(j, _ int) {
			noiseValue := evaluatePerlinNoise(v3{float32(i) / 256.0, float32(j) / 256.0, 0}, noise, noiseSettings)
			twoDArray[i][j] = uint8(noiseValue * 256)
		})
	})

	return twoDArray
}
