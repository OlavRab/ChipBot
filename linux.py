import subprocess

x = subprocess.run(['df -h /home --output=avail,used,size'], shell=True, capture_output=True)
# x = subprocess.run(['df -h'], shell=True, capture_output=True)

# print(x.args)
# print(x.returncode)
# print(x.stderr)
output = str(x.stdout)

split_output = output.split(" ")

print(split_output)

available = split_output[6]
used = split_output[8]
total = split_output[11]
print(total)

available_memory = int(available.split("G")[0])
used_memory = float(used.split("G")[0])

percentage = (used_memory/available_memory)*100

print("The current memory available: \n Used Space: " + str(available_memory) + " Gigabytes\n Free Space: " + str(used_memory)+ " Gigabytes")
