/**
  ******************************************************************************
  * @file    st7789.h
  * @brief   Driver ST7789 IPS LCD (240x240) cho STM32F401CCU6 (GMT130-V1.0)
  ******************************************************************************
  */

#ifndef __ST7789_H
#define __ST7789_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "fonts.h"
#include <string.h>
#include <stdlib.h>

/* ========================================================================== */
/*                           CẤU HÌNH PHẦN CỨNG                              */
/* ========================================================================== */
/* Handle SPI sử dụng */
extern SPI_HandleTypeDef hspi1;
#define ST7789_SPI_PORT      hspi1

/* Định nghĩa chân điều khiển cho Module GMT130-V1.0 theo thực tế cắm dây */
#define ST7789_RES_PORT      GPIOA
#define ST7789_RES_PIN       GPIO_PIN_2    /* Chân PA2 (Dây Vàng - RES) */

#define ST7789_DC_PORT       GPIOA
#define ST7789_DC_PIN        GPIO_PIN_3    /* Chân PA3 (Dây Cam - DC) */

#define ST7789_BLK_PORT      GPIOA
#define ST7789_BLK_PIN       GPIO_PIN_1    /* Chân PA1 (Dự phòng, đèn nền đã tự sáng qua VCC) */

/* Kích thước màn hình */
#define ST7789_WIDTH         240
#define ST7789_HEIGHT        240

/* Offset toạ độ nếu panel bị dịch (mặc định 240x240 là 0) */
#define ST7789_XSTART        0
#define ST7789_YSTART        0

/* ========================================================================== */
/*                              MÃ LỆNH ST7789                                */
/* ========================================================================== */
#define ST7789_CMD_NOP       0x00
#define ST7789_CMD_SWRESET   0x01
#define ST7789_CMD_SLPIN     0x10
#define ST7789_CMD_SLPOUT    0x11
#define ST7789_CMD_NORON     0x13
#define ST7789_CMD_INVOFF    0x20
#define ST7789_CMD_INVON     0x21
#define ST7789_CMD_DISPOFF   0x28
#define ST7789_CMD_DISPON    0x29
#define ST7789_CMD_CASET     0x2A
#define ST7789_CMD_RASET     0x2B
#define ST7789_CMD_RAMWR     0x2C
#define ST7789_CMD_MADCTL    0x36
#define ST7789_CMD_COLMOD    0x3A

#define ST7789_MADCTL_MY     0x80
#define ST7789_MADCTL_MX     0x40
#define ST7789_MADCTL_MV     0x20
#define ST7789_MADCTL_ML     0x10
#define ST7789_MADCTL_BGR    0x08
#define ST7789_MADCTL_RGB    0x00

/* ========================================================================== */
/*                             MÀU SẮC (RGB565)                               */
/* ========================================================================== */
#define ST7789_COLOR565(r, g, b)  ((((r) & 0xF8) << 8) | (((g) & 0xFC) << 3) | ((b) >> 3))

#define ST7789_BLACK         0x0000
#define ST7789_WHITE         0xFFFF
#define ST7789_RED           0xF800
#define ST7789_GREEN         0x07E0
#define ST7789_BLUE          0x001F
#define ST7789_CYAN          0x07FF
#define ST7789_MAGENTA       0xF81F
#define ST7789_YELLOW        0xFFE0
#define ST7789_ORANGE        0xFD20
#define ST7789_DARKGREY      0x39E7
#define ST7789_LIGHTGREY     0xC618
#define ST7789_NAVY          0x000F
#define ST7789_PURPLE        0x780F
#define ST7789_GOLD          0xFEA0
#define ST7789_DARKBLUE      0x08A5
#define ST7789_TEAL          0x0410

/* ========================================================================== */
/*                               KHAI BÁO HÀM                                 */
/* ========================================================================== */
void ST7789_Init(void);
void ST7789_Backlight(uint8_t state);
void ST7789_SetRotation(uint8_t m);
void ST7789_InvertColors(uint8_t invert);
void ST7789_SetAddressWindow(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);

/* Vẽ cơ bản */
void ST7789_Fill(uint16_t color);
void ST7789_DrawPixel(uint16_t x, uint16_t y, uint16_t color);
void ST7789_FillRect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color);
void ST7789_DrawRect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color);
void ST7789_DrawLine(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t color);
void ST7789_DrawFastHLine(uint16_t x, uint16_t y, uint16_t w, uint16_t color);
void ST7789_DrawFastVLine(uint16_t x, uint16_t y, uint16_t h, uint16_t color);
void ST7789_DrawCircle(uint16_t x0, uint16_t y0, int16_t r, uint16_t color);
void ST7789_FillCircle(uint16_t x0, uint16_t y0, int16_t r, uint16_t color);

/* Hiển thị ký tự & chuỗi văn bản */
void ST7789_DrawChar(uint16_t x, uint16_t y, char ch, FontDef font, uint16_t color, uint16_t bgcolor);
void ST7789_WriteString(uint16_t x, uint16_t y, const char *str, FontDef font, uint16_t color, uint16_t bgcolor);

/* Hàm Test demo toàn diện */
void ST7789_TestDemo(void);

#ifdef __cplusplus
}
#endif

#endif /* __ST7789_H */
