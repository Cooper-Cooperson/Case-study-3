FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
COPY views ./views
RUN npm install --production

COPY . .

EXPOSE 8080
CMD ["npm", "start"]