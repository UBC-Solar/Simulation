package main

type v3i = [3]int32
type v3 = [3]float32
type v2i = [2]int32

var v3Zero = v3{0, 0, 0}

func v3ScalarMultiply(vector v3, scalar float32) v3 {
	vector[0] *= scalar
	vector[1] *= scalar
	vector[2] *= scalar

	return vector
}

func v3Add(vector v3, other v3) v3 {
	vector[0] += other[0]
	vector[1] += other[1]
	vector[2] += other[2]

	return vector
}
