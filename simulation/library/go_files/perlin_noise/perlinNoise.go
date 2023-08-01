package main

type NoiseSettings struct {
	strength      float32
	baseRoughness float32
	roughness     float32
	centre        v3
	numLayers     int32
	persistence   float32
}

func evaluateSimplexNoise(point v3, noise *Noise, noiseSettings *NoiseSettings) float32 {
	noiseValue := evaluateNoise(v3Add(v3ScalarMultiply(point, noiseSettings.roughness), noiseSettings.centre), noise)
	return noiseValue * noiseSettings.strength
}

func evaluatePerlinNoise(point v3, noise *Noise, noiseSettings *NoiseSettings) float32 {
	var noiseValue float32 = 0
	frequency := noiseSettings.baseRoughness
	var amplitude float32 = 1

	for i := 0; int32(i) < noiseSettings.numLayers; i++ {
		v := evaluateNoise(v3Add(v3ScalarMultiply(point, frequency), noiseSettings.centre), noise)
		noiseValue += (v + 1) * 0.5 * amplitude
		frequency *= noiseSettings.roughness
		amplitude *= noiseSettings.persistence
	}

	return noiseValue * noiseSettings.strength
}
