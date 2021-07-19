import matplotlib.pyplot as plt
import time
import requests
  
url = "https://api.coincap.io/v2/assets/ethereum/history?interval=d1"
response = requests.get(url).json()


time = []
value = []

i = 1
while i < 30:
    time.append(response['data'][i]['date'])
    value.append(float(response['data'][i]['priceUsd']))
    i = i + 1

# print(value)
# print(time)
plt.plot(time, value)
  
# naming the x axis
plt.xlabel('x - axis')
# naming the y axis
plt.ylabel('y - axis')
  
# giving a title to my graph
plt.title('My first graph!')

plt.savefig('test.png')