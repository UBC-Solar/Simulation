package main

import "C"
import (
	"github.com/dgravesa/go-parallel/parallel"
	"unsafe"
)
import (
	_ "image/jpeg"
)

// GOARCH=arm64 GOOS=darwin CGO_ENABLED=1 go build -o perlin_noise.so -buildmode=c-shared main/src

//export generatePerlinNoise
func generatePerlinNoise(resultPtr *float32,
	width uint32,
	height uint32,
	persistence float32,
	numLayers uint32,
	roughness float32,
	baseRoughness float32,
	strength float32,
	randomSeed uint32) {

	settings := &NoiseSettings{
		Strength:      strength,
		baseRoughness: baseRoughness,
		roughness:     roughness,
		centre:        v3Zero,
		numLayers:     numLayers,
		persistence:   persistence,
	}

	noise := generateSimplexNoise(randomSeed)

	result := unsafe.Slice(resultPtr, width*height)

	parallel.For(int(width), func(i, _ int) {
		parallel.For(int(height), func(j, _ int) {
			noiseValue := evaluatePerlinNoise(v3{float32(i) / float32(width), float32(j) / float32(height), 0}, noise, settings)
			result[(i*int(width))+j] = noiseValue
		})
	})
}

func main() {

}
