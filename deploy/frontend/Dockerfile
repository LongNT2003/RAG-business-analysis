# frontend/Dockerfile

# Base image để chạy Node.js
FROM node:18-alpine 

# Tạo và set thư mục làm việc
WORKDIR /app 

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all files
COPY . .

# Make sure files are accessible
RUN chmod -R 755 .

EXPOSE 5000

CMD ["npm", "start"]