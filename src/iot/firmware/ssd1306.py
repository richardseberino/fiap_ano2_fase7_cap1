# Driver mínimo do display OLED SSD1306 (I2C) baseado em framebuf.
# Compatível com o driver oficial do micropython-lib para o uso deste projeto.
import framebuf


class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, largura, altura, i2c, endereco=0x3C):
        self.largura = largura
        self.altura = altura
        self.i2c = i2c
        self.endereco = endereco
        self.paginas = altura // 8
        self.buffer = bytearray(self.paginas * largura)
        super().__init__(self.buffer, largura, altura, framebuf.MONO_VLSB)
        for comando in (
            0xAE,                    # display off
            0x20, 0x00,              # endereçamento horizontal
            0x40,                    # linha inicial 0
            0xA1,                    # remapeamento de segmento
            0xA8, altura - 1,        # multiplex
            0xC8,                    # varredura COM invertida
            0xD3, 0x00,              # offset
            0xDA, 0x12 if altura == 64 else 0x02,
            0xD5, 0x80,              # clock
            0xD9, 0xF1,              # pré-carga
            0xDB, 0x30,              # VCOM
            0x81, 0xFF,              # contraste
            0xA4, 0xA6,              # exibe RAM, não invertido
            0x8D, 0x14,              # charge pump
            0xAF,                    # display on
        ):
            self._comando(comando)
        self.fill(0)
        self.show()

    def _comando(self, comando):
        self.i2c.writeto(self.endereco, bytearray((0x80, comando)))

    def show(self):
        for comando in (0x21, 0, self.largura - 1, 0x22, 0, self.paginas - 1):
            self._comando(comando)
        self.i2c.writeto(self.endereco, b"\x40" + self.buffer)
