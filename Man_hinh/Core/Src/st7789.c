/**
  ******************************************************************************
  * @file    st7789.c
  * @brief   Driver ST7789 IPS LCD (240x240) cho STM32F401CCU6 (GMT130-V1.0)
  ******************************************************************************
  */

#include "st7789.h"
#include <stdio.h>

/* Biến lưu trữ toạ độ offset theo góc xoay */
static uint16_t ST7789_X_Offset = ST7789_XSTART;
static uint16_t ST7789_Y_Offset = ST7789_YSTART;
static uint8_t  ST7789_Current_Rotation = 0;

/* Macro điều khiển chân GPIO */
#define ST7789_RES_LOW()   HAL_GPIO_WritePin(ST7789_RES_PORT, ST7789_RES_PIN, GPIO_PIN_RESET)
#define ST7789_RES_HIGH()  HAL_GPIO_WritePin(ST7789_RES_PORT, ST7789_RES_PIN, GPIO_PIN_SET)
#define ST7789_DC_CMD()    HAL_GPIO_WritePin(ST7789_DC_PORT, ST7789_DC_PIN, GPIO_PIN_RESET)
#define ST7789_DC_DATA()   HAL_GPIO_WritePin(ST7789_DC_PORT, ST7789_DC_PIN, GPIO_PIN_SET)
#define ST7789_BLK_HIGH()  HAL_GPIO_WritePin(ST7789_BLK_PORT, ST7789_BLK_PIN, GPIO_PIN_SET)
#define ST7789_BLK_LOW()   HAL_GPIO_WritePin(ST7789_BLK_PORT, ST7789_BLK_PIN, GPIO_PIN_RESET)

/* ========================================================================== */
/*                           HÀM GIAO TIẾP SPI CƠ BẢN                         */
/* ========================================================================== */

/**
  * @brief  Gửi 1 byte lệnh tới ST7789 (DC = 0)
  */
static void ST7789_WriteCommand(uint8_t cmd)
{
    ST7789_DC_CMD();
    HAL_SPI_Transmit(&ST7789_SPI_PORT, &cmd, 1, HAL_MAX_DELAY);
}

/**
  * @brief  Gửi mảng dữ liệu tới ST7789 (DC = 1)
  */
static void ST7789_WriteData(uint8_t *buff, size_t buff_size)
{
    ST7789_DC_DATA();
    /* Với khối dữ liệu lớn hơn 65535 byte, chia nhỏ để truyền */
    while (buff_size > 0)
    {
        uint16_t chunk = (buff_size > 65535) ? 65535 : (uint16_t)buff_size;
        HAL_SPI_Transmit(&ST7789_SPI_PORT, buff, chunk, HAL_MAX_DELAY);
        buff += chunk;
        buff_size -= chunk;
    }
}

/**
  * @brief  Gửi 1 byte dữ liệu tới ST7789
  */
static void ST7789_WriteSmallData(uint8_t data)
{
    ST7789_DC_DATA();
    HAL_SPI_Transmit(&ST7789_SPI_PORT, &data, 1, HAL_MAX_DELAY);
}

/* ========================================================================== */
/*                             CẤU HÌNH & KHỞI TẠO                            */
/* ========================================================================== */

/**
  * @brief  Bật/tắt đèn nền màn hình (Backlight)
  */
void ST7789_Backlight(uint8_t state)
{
    if (state)
    {
        ST7789_BLK_HIGH();
    }
    else
    {
        ST7789_BLK_LOW();
    }
}

/**
  * @brief  Đảo màu màn hình (Invert Colors)
  */
void ST7789_InvertColors(uint8_t invert)
{
    ST7789_WriteCommand(invert ? ST7789_CMD_INVON : ST7789_CMD_INVOFF);
}

/**
  * @brief  Cài đặt góc xoay màn hình (0: 0°, 1: 90°, 2: 180°, 3: 270°)
  */
void ST7789_SetRotation(uint8_t m)
{
    ST7789_Current_Rotation = m % 4;
    ST7789_WriteCommand(ST7789_CMD_MADCTL);

    switch (ST7789_Current_Rotation)
    {
    case 0:
        ST7789_WriteSmallData(ST7789_MADCTL_RGB);
        ST7789_X_Offset = 0;
        ST7789_Y_Offset = 0;
        break;
    case 1:
        ST7789_WriteSmallData(ST7789_MADCTL_MX | ST7789_MADCTL_MV | ST7789_MADCTL_RGB);
        ST7789_X_Offset = 0;
        ST7789_Y_Offset = 0;
        break;
    case 2:
        ST7789_WriteSmallData(ST7789_MADCTL_MX | ST7789_MADCTL_MY | ST7789_MADCTL_RGB);
        ST7789_X_Offset = 0;
        ST7789_Y_Offset = 80; /* ST7789 có RAM 240x320, panel 240x240 cần bù 80px khi lộn ngược */
        break;
    case 3:
        ST7789_WriteSmallData(ST7789_MADCTL_MY | ST7789_MADCTL_MV | ST7789_MADCTL_RGB);
        ST7789_X_Offset = 80;
        ST7789_Y_Offset = 0;
        break;
    }
}

/**
  * @brief  Thiết lập cửa sổ vẽ (Address Window)
  */
void ST7789_SetAddressWindow(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    uint16_t x_start = x0 + ST7789_X_Offset;
    uint16_t x_end   = x1 + ST7789_X_Offset;
    uint16_t y_start = y0 + ST7789_Y_Offset;
    uint16_t y_end   = y1 + ST7789_Y_Offset;

    /* Đặt dải cột */
    ST7789_WriteCommand(ST7789_CMD_CASET);
    uint8_t caset_data[4] = {
        (uint8_t)(x_start >> 8), (uint8_t)(x_start & 0xFF),
        (uint8_t)(x_end >> 8),   (uint8_t)(x_end & 0xFF)
    };
    ST7789_WriteData(caset_data, 4);

    /* Đặt dải hàng */
    ST7789_WriteCommand(ST7789_CMD_RASET);
    uint8_t raset_data[4] = {
        (uint8_t)(y_start >> 8), (uint8_t)(y_start & 0xFF),
        (uint8_t)(y_end >> 8),   (uint8_t)(y_end & 0xFF)
    };
    ST7789_WriteData(raset_data, 4);

    /* Bắt đầu ghi dữ liệu pixel vào RAM */
    ST7789_WriteCommand(ST7789_CMD_RAMWR);
}

/**
  * @brief  Khởi tạo màn hình ST7789 GMT130-V1.0
  */
void ST7789_Init(void)
{
    /* 1. Reset phần cứng qua chân RES với thời gian xả tụ kỹ lưỡng */
    ST7789_RES_HIGH();
    HAL_Delay(50);
    ST7789_RES_LOW();
    HAL_Delay(100);
    ST7789_RES_HIGH();
    HAL_Delay(150);

    /* 2. Kích hoạt chân BLK (nếu có cắm vào PA1) */
    ST7789_Backlight(1);

    /* 3. Software Reset */
    ST7789_WriteCommand(ST7789_CMD_SWRESET);
    HAL_Delay(150);

    /* 4. Thoát chế độ Sleep */
    ST7789_WriteCommand(ST7789_CMD_SLPOUT);
    HAL_Delay(150);

    /* 5. Cài đặt định dạng màu: 16-bit/pixel RGB565 */
    ST7789_WriteCommand(ST7789_CMD_COLMOD);
    ST7789_WriteSmallData(0x55);
    HAL_Delay(10);

    /* 6. Hướng quét màn hình */
    ST7789_SetRotation(0);
    HAL_Delay(10);

    /* 7. Bật chế độ Inversion (chuẩn tấm nền IPS) */
    ST7789_WriteCommand(ST7789_CMD_INVON);
    HAL_Delay(10);

    /* 8. Chế độ hiển thị bình thường */
    ST7789_WriteCommand(ST7789_CMD_NORON);
    HAL_Delay(10);

    /* 9. Bật màn hình hiển thị (Display ON) */
    ST7789_WriteCommand(ST7789_CMD_DISPON);
    HAL_Delay(150);

    /* 10. Chớp màu Đỏ -> Xanh lá -> Xanh dương để kiểm tra ngay panel */
    ST7789_Fill(ST7789_RED);
    HAL_Delay(400);
    ST7789_Fill(ST7789_GREEN);
    HAL_Delay(400);
    ST7789_Fill(ST7789_BLUE);
    HAL_Delay(400);
    ST7789_Fill(ST7789_BLACK);
}

/* ========================================================================== */
/*                            CÁC HÀM VẼ ĐỒ HOẠ                               */
/* ========================================================================== */

/**
  * @brief  Vẽ 1 pixel tại toạ độ (x, y) với màu color (RGB565)
  */
void ST7789_DrawPixel(uint16_t x, uint16_t y, uint16_t color)
{
    if (x >= ST7789_WIDTH || y >= ST7789_HEIGHT) return;

    ST7789_SetAddressWindow(x, y, x, y);
    uint8_t data[2] = {(uint8_t)(color >> 8), (uint8_t)(color & 0xFF)};
    ST7789_WriteData(data, 2);
}

/**
  * @brief  Vẽ hình chữ nhật đặc màu (Filled Rectangle) tốc độ cao
  */
void ST7789_FillRect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color)
{
    if (x >= ST7789_WIDTH || y >= ST7789_HEIGHT || w == 0 || h == 0) return;
    if ((x + w - 1) >= ST7789_WIDTH)  w = ST7789_WIDTH - x;
    if ((y + h - 1) >= ST7789_HEIGHT) h = ST7789_HEIGHT - y;

    ST7789_SetAddressWindow(x, y, x + w - 1, y + h - 1);

    /* Tạo bộ đệm nhỏ 240 pixel (480 bytes) để truyền nhanh qua SPI */
    #define FILL_BUFFER_PIXELS 240
    static uint8_t buffer[FILL_BUFFER_PIXELS * 2];
    uint8_t c_hi = (uint8_t)(color >> 8);
    uint8_t c_lo = (uint8_t)(color & 0xFF);

    for (uint32_t i = 0; i < FILL_BUFFER_PIXELS * 2; i += 2)
    {
        buffer[i]     = c_hi;
        buffer[i + 1] = c_lo;
    }

    uint32_t total_pixels = (uint32_t)w * h;
    while (total_pixels > 0)
    {
        uint32_t chunk = (total_pixels > FILL_BUFFER_PIXELS) ? FILL_BUFFER_PIXELS : total_pixels;
        ST7789_WriteData(buffer, chunk * 2);
        total_pixels -= chunk;
    }
}

/**
  * @brief  Xoá toàn bộ màn hình với 1 màu duy nhất
  */
void ST7789_Fill(uint16_t color)
{
    ST7789_FillRect(0, 0, ST7789_WIDTH, ST7789_HEIGHT, color);
}

/**
  * @brief  Vẽ đường thẳng nằm ngang (cực nhanh)
  */
void ST7789_DrawFastHLine(uint16_t x, uint16_t y, uint16_t w, uint16_t color)
{
    ST7789_FillRect(x, y, w, 1, color);
}

/**
  * @brief  Vẽ đường thẳng đứng (cực nhanh)
  */
void ST7789_DrawFastVLine(uint16_t x, uint16_t y, uint16_t h, uint16_t color)
{
    ST7789_FillRect(x, y, 1, h, color);
}

/**
  * @brief  Vẽ khung hình chữ nhật rỗng
  */
void ST7789_DrawRect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color)
{
    ST7789_DrawFastHLine(x, y, w, color);
    ST7789_DrawFastHLine(x, y + h - 1, w, color);
    ST7789_DrawFastVLine(x, y, h, color);
    ST7789_DrawFastVLine(x + w - 1, y, h, color);
}

/**
  * @brief  Vẽ đoạn thẳng bất kỳ (Thuật toán Bresenham)
  */
void ST7789_DrawLine(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1, uint16_t color)
{
    int16_t steep = abs((int16_t)y1 - (int16_t)y0) > abs((int16_t)x1 - (int16_t)x0);
    if (steep)
    {
        uint16_t temp;
        temp = x0; x0 = y0; y0 = temp;
        temp = x1; x1 = y1; y1 = temp;
    }

    if (x0 > x1)
    {
        uint16_t temp;
        temp = x0; x0 = x1; x1 = temp;
        temp = y0; y0 = y1; y1 = temp;
    }

    int16_t dx = (int16_t)x1 - (int16_t)x0;
    int16_t dy = abs((int16_t)y1 - (int16_t)y0);
    int16_t err = dx / 2;
    int16_t ystep = (y0 < y1) ? 1 : -1;
    int16_t y = y0;

    for (int16_t x = x0; x <= x1; x++)
    {
        if (steep)
        {
            ST7789_DrawPixel(y, x, color);
        }
        else
        {
            ST7789_DrawPixel(x, y, color);
        }
        err -= dy;
        if (err < 0)
        {
            y += ystep;
            err += dx;
        }
    }
}

/**
  * @brief  Vẽ đường tròn rỗng
  */
void ST7789_DrawCircle(uint16_t x0, uint16_t y0, int16_t r, uint16_t color)
{
    int16_t f = 1 - r;
    int16_t ddF_x = 1;
    int16_t ddF_y = -2 * r;
    int16_t x = 0;
    int16_t y = r;

    ST7789_DrawPixel(x0, y0 + r, color);
    ST7789_DrawPixel(x0, y0 - r, color);
    ST7789_DrawPixel(x0 + r, y0, color);
    ST7789_DrawPixel(x0 - r, y0, color);

    while (x < y)
    {
        if (f >= 0)
        {
            y--;
            ddF_y += 2;
            f += ddF_y;
        }
        x++;
        ddF_x += 2;
        f += ddF_x;

        ST7789_DrawPixel(x0 + x, y0 + y, color);
        ST7789_DrawPixel(x0 - x, y0 + y, color);
        ST7789_DrawPixel(x0 + x, y0 - y, color);
        ST7789_DrawPixel(x0 - x, y0 - y, color);
        ST7789_DrawPixel(x0 + y, y0 + x, color);
        ST7789_DrawPixel(x0 - y, y0 + x, color);
        ST7789_DrawPixel(x0 + y, y0 - x, color);
        ST7789_DrawPixel(x0 - y, y0 - x, color);
    }
}

/**
  * @brief  Vẽ hình tròn đặc
  */
void ST7789_FillCircle(uint16_t x0, uint16_t y0, int16_t r, uint16_t color)
{
    ST7789_DrawFastVLine(x0, y0 - r, 2 * r + 1, color);

    int16_t f = 1 - r;
    int16_t ddF_x = 1;
    int16_t ddF_y = -2 * r;
    int16_t x = 0;
    int16_t y = r;

    while (x < y)
    {
        if (f >= 0)
        {
            y--;
            ddF_y += 2;
            f += ddF_y;
        }
        x++;
        ddF_x += 2;
        f += ddF_x;

        ST7789_DrawFastVLine(x0 + x, y0 - y, 2 * y + 1, color);
        ST7789_DrawFastVLine(x0 - x, y0 - y, 2 * y + 1, color);
        ST7789_DrawFastVLine(x0 + y, y0 - x, 2 * x + 1, color);
        ST7789_DrawFastVLine(x0 - y, y0 - x, 2 * x + 1, color);
    }
}

/* ========================================================================== */
/*                        HIỂN THỊ CHỮ (TEXT & FONTS)                         */
/* ========================================================================== */

/**
  * @brief  Vẽ 1 ký tự ASCII lên màn hình bằng Burst Window (siêu tốc)
  */
void ST7789_DrawChar(uint16_t x, uint16_t y, char ch, FontDef font, uint16_t color, uint16_t bgcolor)
{
    if (ch < 32 || ch > 126) return;
    if (x + font.width > ST7789_WIDTH || y + font.height > ST7789_HEIGHT) return;

    /* Mở cửa sổ vẽ đúng kích thước ký tự */
    ST7789_SetAddressWindow(x, y, x + font.width - 1, y + font.height - 1);

    uint32_t char_index = (ch - 32) * font.height;
    uint8_t c_hi = (uint8_t)(color >> 8);
    uint8_t c_lo = (uint8_t)(color & 0xFF);
    uint8_t bg_hi = (uint8_t)(bgcolor >> 8);
    uint8_t bg_lo = (uint8_t)(bgcolor & 0xFF);

    /* Bộ đệm chứa các pixel của ký tự (font lớn nhất 16x26 = 416 pixels = 832 bytes) */
    uint8_t char_buf[16 * 26 * 2];
    uint32_t buf_idx = 0;

    for (uint8_t row = 0; row < font.height; row++)
    {
        uint16_t b = font.data[char_index + row];
        for (uint8_t col = 0; col < font.width; col++)
        {
            if ((b << col) & 0x8000)
            {
                char_buf[buf_idx++] = c_hi;
                char_buf[buf_idx++] = c_lo;
            }
            else
            {
                char_buf[buf_idx++] = bg_hi;
                char_buf[buf_idx++] = bg_lo;
            }
        }
    }
    ST7789_WriteData(char_buf, buf_idx);
}

/**
  * @brief  Vẽ chuỗi ký tự với font và màu tuỳ chọn
  */
void ST7789_WriteString(uint16_t x, uint16_t y, const char *str, FontDef font, uint16_t color, uint16_t bgcolor)
{
    uint16_t cur_x = x;
    uint16_t cur_y = y;

    while (*str)
    {
        if (*str == '\n')
        {
            cur_x = x;
            cur_y += font.height + 2;
            str++;
            continue;
        }

        if (cur_x + font.width > ST7789_WIDTH)
        {
            cur_x = x;
            cur_y += font.height + 2;
        }

        if (cur_y + font.height > ST7789_HEIGHT)
        {
            break;
        }

        ST7789_DrawChar(cur_x, cur_y, *str, font, color, bgcolor);
        cur_x += font.width;
        str++;
    }
}

/* ========================================================================== */
/*                             HÀM TEST DEMO                                  */
/* ========================================================================== */

/**
  * @brief  Trình diễn demo toàn diện kiểm tra màn hình GMT130-V1.0
  */
void ST7789_TestDemo(void)
{
    /* 1. Kiểm tra 3 màu cơ bản & màn hình đen trắng để soi điểm chết / tấm nền IPS */
    ST7789_Fill(ST7789_RED);
    HAL_Delay(350);
    ST7789_Fill(ST7789_GREEN);
    HAL_Delay(350);
    ST7789_Fill(ST7789_BLUE);
    HAL_Delay(350);
    ST7789_Fill(ST7789_WHITE);
    HAL_Delay(350);
    ST7789_Fill(ST7789_BLACK);
    HAL_Delay(200);

    /* 2. Giao diện chào mừng theo phong cách hiện đại */
    /* Header Bar */
    ST7789_FillRect(0, 0, 240, 36, ST7789_NAVY);
    ST7789_DrawFastHLine(0, 36, 240, ST7789_CYAN);
    ST7789_WriteString(16, 8, "STM32F401 x ST7789", Font_11x18, ST7789_WHITE, ST7789_NAVY);

    /* Dải màu Test Color Palette */
    uint16_t palette[] = {ST7789_RED, ST7789_GREEN, ST7789_BLUE, ST7789_YELLOW, ST7789_CYAN, ST7789_MAGENTA};
    for (uint8_t i = 0; i < 6; i++)
    {
        ST7789_FillRect(12 + i * 36, 45, 32, 14, palette[i]);
        ST7789_DrawRect(12 + i * 36, 45, 32, 14, ST7789_WHITE);
    }

    /* Khung thông tin màn hình */
    ST7789_DrawRect(10, 68, 220, 72, ST7789_DARKGREY);
    ST7789_WriteString(18, 74, "GMT130-V1.0 1.3\" IPS", Font_7x10, ST7789_GOLD, ST7789_BLACK);
    ST7789_WriteString(18, 90, "Res: 240x240 RGB565", Font_7x10, ST7789_CYAN, ST7789_BLACK);
    ST7789_WriteString(18, 106, "65K Colors (SPI Mode)", Font_7x10, ST7789_GREEN, ST7789_BLACK);
    ST7789_WriteString(18, 122, "Goodbye SSD1306 :D", Font_7x10, ST7789_YELLOW, ST7789_BLACK);

    /* Hình học họa tiết (Concentric Circles & Shapes) */
    ST7789_DrawCircle(45, 178, 24, ST7789_RED);
    ST7789_DrawCircle(45, 178, 16, ST7789_GREEN);
    ST7789_FillCircle(45, 178, 8, ST7789_BLUE);

    ST7789_DrawRect(85, 155, 45, 45, ST7789_ORANGE);
    ST7789_FillRect(95, 165, 25, 25, ST7789_PURPLE);

    /* Chữ to Font 16x26 */
    ST7789_WriteString(145, 162, "OK!", Font_16x26, ST7789_GREEN, ST7789_BLACK);

    /* Thanh Progress Bar minh hoạ */
    ST7789_DrawRect(10, 215, 220, 16, ST7789_WHITE);
    for (uint8_t p = 0; p <= 216; p += 4)
    {
        ST7789_FillRect(12, 217, p, 12, ST7789_CYAN);
        HAL_Delay(10);
    }
}
