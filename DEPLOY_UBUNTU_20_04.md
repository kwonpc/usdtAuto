# Ubuntu 20.04 Minimal 배포 가이드

Oracle Cloud `VM.Standard.E2.1.Micro` + Ubuntu Minimal 20.04 + 기본 `docker-compose` 기준입니다.

## 1. 로컬에서 SSH 접속

기존 VM을 지우고 같은 Public IP를 재사용했다면 먼저 known hosts를 정리합니다.

```powershell
ssh-keygen -R VM_PUBLIC_IP
```

Ubuntu VM 기본 계정은 `ubuntu`입니다.

```powershell
ssh -i C:\path\to\oracle_vm.key ubuntu@VM_PUBLIC_IP
```

## 2. VM 기본 패키지 설치

Ubuntu 20.04 기본 저장소의 `docker-compose`는 구버전입니다. `docker compose`가 아니라 `docker-compose` 명령을 사용합니다.

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose unzip
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu
exit
```

권한 적용을 위해 SSH를 다시 접속합니다.

```powershell
ssh -i C:\path\to\oracle_vm.key ubuntu@VM_PUBLIC_IP
```

설치 확인:

```bash
docker --version
docker-compose --version
```

## 3. 소스 내려받기

```bash
git clone https://github.com/kwonpc/usdtAuto.git
cd usdtAuto
```

## 4. Oracle Wallet 업로드

로컬 PowerShell에서 실행합니다.

```powershell
scp -i C:\path\to\oracle_vm.key -r C:\path\to\Wallet_DBNAME ubuntu@VM_PUBLIC_IP:/home/ubuntu/usdtAuto/wallet
```

VM에서 확인:

```bash
cd ~/usdtAuto
ls -la wallet
```

`tnsnames.ora`, `sqlnet.ora`, `cwallet.sso`, `ewallet.p12`, `ewallet.pem` 등이 보여야 합니다.

## 5. config.yml 설정

VM에서:

```bash
cd ~/usdtAuto
nano config.yml
```

아래 값으로 수정합니다.

```yaml
database_url: oracle+oracledb://USTDAUTO:DB_PASSWORD@nu1if80z6t7asdcl_low
oracle_wallet_dir: /app/wallet
oracle_wallet_password: WALLET_PASSWORD
```

예시의 `DB_PASSWORD`, `WALLET_PASSWORD`는 실제 값으로 바꿉니다.

## 6. docker-compose.yml 수정

Ubuntu 20.04 기본 `docker-compose`는 최신 compose spec을 제대로 읽지 못할 수 있으므로 `version: "3.3"`을 명시합니다.

```bash
nano docker-compose.yml
```

아래 형태로 맞춥니다.

```yaml
version: "3.3"

services:
  trading-bot:
    build: .
    container_name: krw-usdt-trading-bot
    ports:
      - "8000:8000"
    volumes:
      - ./config.yml:/app/config.yml:ro
      - ./data:/app/data
      - ./wallet:/app/wallet:ro
    environment:
      - TZ=Asia/Seoul
    restart: unless-stopped
```

문법 확인:

```bash
docker-compose config
```

## 7. 앱 실행

```bash
mkdir -p data
docker-compose up -d --build
docker-compose logs -f
```

로그에서 Uvicorn이 아래처럼 떠야 합니다.

```text
Uvicorn running on http://0.0.0.0:8000
```

로그 종료는 `Ctrl+C`입니다. 컨테이너는 계속 실행됩니다.

## 8. 상태 확인

```bash
docker-compose ps
curl http://127.0.0.1:8000/
```

브라우저에서 접속:

```text
http://VM_PUBLIC_IP:8000/
```

외부에서 안 열리면 Oracle Cloud 콘솔에서 VM의 Security List 또는 NSG에 인바운드 규칙을 추가합니다.

```text
Source: 내 공인 IP/32
IP Protocol: TCP
Destination Port: 8000
```

## 9. 재배포

코드 업데이트:

```bash
cd ~/usdtAuto
git pull
docker-compose up -d --build
docker-compose logs -f
```

## 10. 자주 쓰는 명령

```bash
docker-compose ps
docker-compose logs -f
docker-compose restart
docker-compose down
docker images
docker ps
```

## 문제 해결

### docker-compose.yml Unsupported config option

`docker-compose.yml` 맨 위에 아래가 있는지 확인합니다.

```yaml
version: "3.3"
```

그리고 서비스는 반드시 `services:` 아래에 있어야 합니다.

### docker-compose-plugin 패키지를 못 찾음

Ubuntu 20.04 기본 저장소에서는 없을 수 있습니다. 대신 아래를 사용합니다.

```bash
sudo apt install -y docker-compose
```

실행 명령도 `docker compose`가 아니라 `docker-compose`입니다.

### Oracle Wallet 파일을 못 찾음

컨테이너 안에서는 wallet 경로가 `/app/wallet`이어야 합니다.

```yaml
oracle_wallet_dir: /app/wallet
```

그리고 compose에 아래 mount가 있어야 합니다.

```yaml
- ./wallet:/app/wallet:ro
```

### ORA-01950: no privileges on tablespace DATA

SQL Developer에서 관리자 계정으로 실행합니다.

```sql
ALTER USER USTDAUTO QUOTA UNLIMITED ON DATA;
```
