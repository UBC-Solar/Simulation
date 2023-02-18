FROM python:3.10.6
WORKDIR = /Simulation
RUN apt update && apt install -y build-essential
COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
COPY . .
ENV PYTHONPATH "${PYTHONPATH}:$PWD$"
RUN apt install golang-go -y
RUN go build -buildmode=c-shared -o weather_in_time_loop.so simulation/environment/main.go
CMD ["python", "examples/fastest_time_given_distance.py"]
