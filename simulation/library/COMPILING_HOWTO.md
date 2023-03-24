# Compiling binaries for your OS


## Guidelines
To compile Go binaries for your operating system if they don't already 
exist so that your instance of Simulation can use GoLang 
implementations, compile main.go in the `go_files` folder. 
Here is how this generally may be done.\
You may need to search StackOverflow or similar for instructions for your specific OS and platform.
Individual Go files for each function are included in case they are needed. You **only need to compile `main.go`**.


In your terminal and in this directory: \
`GOOS={Your operating system}`\
`go build -o main.so buildmode=c-shared main.go`\
You may also need to include: \
`GOARCH=amd64` \
and/or\
`CGO_ENABLED=1`\
See https://www.digitalocean.com/community/tutorials/building-go-applications-for-different-operating-systems-and-architectures
for a list of keypairs for different operating systems and architectures and how to find yours.

Once `.so` and `.h` files have been compiled, they should be placed into a new folder inside of `library/binaries` 
so that Simulation can find them. Name the folder according to your OS and architecture.

## Example
Compiling on M1 Mac requires the following commands to compile weather_in_time_loop.so:\
`GOOS=darwin GOARCH=amd64 CGO_ENABLED=1 go build -o main.so -buildmode=c-shared main.go` 
