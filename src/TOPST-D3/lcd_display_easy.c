#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>

#define I2C_ADDR 0x27
#define RESULT_FILE "/home/root/emotion_result.txt"

void lcd_send_cmd(int file, char cmd) {
    char data_u, data_l;
    data_u = (cmd & 0xF0) | 0x08;
    data_l = ((cmd << 4) & 0xF0) | 0x08;
    char cmds[4] = {data_u | 0x04, data_u, data_l | 0x04, data_l};
    write(file, cmds, sizeof(cmds));
    usleep(50);
}

void lcd_send_data(int file, char data) {
    char data_u, data_l;
    data_u = (data & 0xF0) | 0x09;
    data_l = ((data << 4) & 0xF0) | 0x09;
    char cmds[4] = {data_u | 0x04, data_u, data_l | 0x04, data_l};
    write(file, cmds, sizeof(cmds));
    usleep(50);
}

void lcd_init(int file) {
    lcd_send_cmd(file, 0x33); // 4비트 모드
    lcd_send_cmd(file, 0x32); // 4비트 모드
    lcd_send_cmd(file, 0x28); // 2라인, 5x8 도트
    lcd_send_cmd(file, 0x0C); // 디스플레이 ON, 커서 OFF
    lcd_send_cmd(file, 0x06); // 커서 이동방향
    lcd_send_cmd(file, 0x01); // 디스플레이 클리어
    usleep(2000);
}

void lcd_display_string(int file, char *str, int line) {
    lcd_send_cmd(file, line == 1 ? 0x80 : 0xC0);
    int cnt = 0;
    while (*str && cnt < 16) { // 16자 제한
        lcd_send_data(file, *str++);
        usleep(100); // 문자 간 대기
        cnt++;
    }
}

int main() {
    int lcd_fd = open("/dev/i2c-1", O_RDWR);
    if (lcd_fd < 0) {
        perror("I2C open failed");
        return -1;
    }
    if (ioctl(lcd_fd, I2C_SLAVE, I2C_ADDR) < 0) {
        perror("I2C slave address set failed");
        close(lcd_fd);
        return -1;
    }
    lcd_init(lcd_fd);

    FILE *f = fopen(RESULT_FILE, "r");
    if (f) {
        char line1[32] = {0}, line2[32] = {0};
        fgets(line1, sizeof(line1), f);
        fgets(line2, sizeof(line2), f);
        line1[strcspn(line1, "\r\n")] = 0;
        line2[strcspn(line2, "\r\n")] = 0;

        printf("Read line1: %s\n", line1);
        printf("Read line2: %s\n", line2);

        lcd_send_cmd(lcd_fd, 0x01); // 클리어
        usleep(20000); // 20ms 대기

        lcd_display_string(lcd_fd, line1, 1);
        lcd_display_string(lcd_fd, line2, 2);
        fclose(f);
    } else {
        perror("Failed to open result file");
        lcd_send_cmd(lcd_fd, 0x01);
        usleep(2000);
        lcd_display_string(lcd_fd, "File Error", 1);
    }

    close(lcd_fd);
    return 0;
}
