#!/bin/bash
set -eo pipefail

COLOR_GREEN=$(tput setaf 2)
COLOR_BLUE=$(tput setaf 4)
COLOR_RED=$(tput setaf 1)
COLOR_NC=$(tput sgr0)

cd "$(dirname "$0")/.."
source ./envs/.prod.env

echo "${COLOR_BLUE}Start CERT Domain with Certbot.."

# ---------- Input Prompt ----------
echo "${COLOR_BLUE}SSL 인증서를 발급받을 도메인을 입력하세요.${COLOR_NC}"
read -p "도메인 주소: " domain
echo ""
echo "${COLOR_BLUE}SSL 인증서를 발급에 사용할 이메일을 입력하세요.${COLOR_NC}"
read -p "이메일: " email
echo ""
echo "${COLOR_BLUE}EC2 인스턴스 생성시 발급받은 ssh key 파일의 파일명을 입력하세요.(ex. ai_health_key.pem)${COLOR_NC}"
read -p "SSH 키 파일명: " ssh_key_file
echo ""
echo "${COLOR_BLUE}EC2 인스턴스의 IP를 입력하세요.${COLOR_NC}"
read -p "EC2-IP: " ec2_ip
echo ""

# ---------- default.conf 파일의 server_name 자동 수정 ----------
sed -i '' "s/server_name .*/server_name ${domain};/g" infra/nginx/prod_http.conf

# ---------- 수정된 prod_http.conf 파일을 EC2 인스턴스 내로 복사 ----------
scp -i ~/.ssh/${ssh_key_file} infra/nginx/prod_http.conf ec2-user@${ec2_ip}:~/project/nginx/default.conf

# ---------- EC2 접속 후 도메인 인증 및 SSL 발급 ----------
echo "${COLOR_BLUE}EC2 인스턴스에 SSH 접속을 시도합니다.${COLOR_NC}"
chmod 400 ~/.ssh/${ssh_key_file}
ssh -i ~/.ssh/${ssh_key_file} ec2-user@${ec2_ip} \
  "CERT_EMAIL=${email} \
   CERT_DOMAIN=${domain} \
   bash -s" << 'EOF'
  set -e
  cd project

  docker compose up -d nginx

  docker run --rm \
    --name certbot \
    -v certbot-conf:/etc/letsencrypt \
    -v certbot-www:/var/www/certbot \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    -d ${CERT_DOMAIN} \
    --agree-tos \
    --email ${CERT_EMAIL} \
    --non-interactive
EOF
echo "${COLOR_GREEN} 도메인 인증서 발급 성공!${COLOR_NC}"
echo ""

# ---------- https 즉시 적용 여부 입력 Prompt ----------
read -p "${COLOR_BLUE} HTTPS를 즉시 서버에 적용하시겠습니까?(Y/N)${COLOR_BLUE}" apply_https
apply_https=$(echo "$apply_https" | tr '[:upper:]' '[:lower:]')

if [[ "$apply_https" == "y" || "$apply_https" == "yes" ]]; then
  # ---------- prod_https.conf 파일의 server_name, ssl_certificate 자동 수정 ----------
  sed -i '' "s/server_name .*/server_name ${domain};/g" infra/nginx/prod_https.conf
  sed -i '' "s|/etc/letsencrypt/live/[^/]*|/etc/letsencrypt/live/${domain}|g" infra/nginx/prod_https.conf

  # ---------- 수정된 prod_http.conf 파일을 EC2 인스턴스 내로 복사 ----------
  scp -i ~/.ssh/${ssh_key_file} infra/nginx/prod_https.conf ec2-user@${ec2_ip}:~/project/nginx/default.conf

  # ---------- EC2 접속 후 SSL 인증서를 적용하여 Nginx를 실행 및 certbot 재발급 서비스 실행 ----------
  ssh -i ~/.ssh/${ssh_key_file} ec2-user@${ec2_ip} \
  "CERT_EMAIL=${email} CERT_DOMAIN=${domain} bash -s" << 'EOF'
      set -e
      cd project

      sudo wget https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
        -O /var/lib/docker/volumes/certbot-conf/_data/options-ssl-nginx.conf
      sudo wget https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem \
        -O /var/lib/docker/volumes/certbot-conf/_data/ssl-dhparams.pem

      docker restart nginx
      docker compose up -d certbot
EOF
  echo "${COLOR_GREEN} https를 적용한 서버 배포 완료!${COLOR_NC}"
  echo ""
else
  echo "${COLOR_BLUE} 스크립트를 종료합니다.${COLOR_NC}"
fi

