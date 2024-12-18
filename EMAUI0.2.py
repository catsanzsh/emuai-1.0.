import tkinter as tk
from tkinter import filedialog, messagebox
import time
from PIL import Image, ImageTk
import struct
import numpy as np

class Memory:
    # N64 Memory Map Constants
    RDRAM_SIZE = 8 * 1024 * 1024  # 8MB
    RDRAM_START = 0x00000000
    RDRAM_END = RDRAM_START + RDRAM_SIZE - 1
    
    PIF_ROM_START = 0x1FC00000
    PIF_ROM_SIZE = 2048
    PIF_ROM_END = PIF_ROM_START + PIF_ROM_SIZE - 1
    
    def __init__(self):
        # Initialize main RAM using numpy for better performance
        self.rdram = np.zeros(self.RDRAM_SIZE, dtype=np.uint8)
        self.pif_rom = np.zeros(self.PIF_ROM_SIZE, dtype=np.uint8)
        
        # Memory stats
        self.reads = 0
        self.writes = 0
        
    def map_address(self, address):
        """Map virtual address to physical memory region"""
        if self.RDRAM_START <= address <= self.RDRAM_END:
            return ("RDRAM", address - self.RDRAM_START)
        elif self.PIF_ROM_START <= address <= self.PIF_ROM_END:
            return ("PIF_ROM", address - self.PIF_ROM_START)
        else:
            raise MemoryError(f"Invalid memory access at address: 0x{address:08X}")

    def read_byte(self, address):
        """Read a single byte from memory"""
        region, offset = self.map_address(address)
        self.reads += 1
        
        if region == "RDRAM":
            return self.rdram[offset]
        elif region == "PIF_ROM":
            return self.pif_rom[offset]

    def write_byte(self, address, value):
        """Write a single byte to memory"""
        region, offset = self.map_address(address)
        self.writes += 1
        
        if region == "RDRAM":
            self.rdram[offset] = value & 0xFF
        elif region == "PIF_ROM":
            # PIF ROM is read-only
            raise MemoryError("Cannot write to PIF ROM")

    def read_word(self, address):
        """Read a 32-bit word from memory"""
        region, offset = self.map_address(address)
        self.reads += 4
        
        if region == "RDRAM":
            return struct.unpack('>I', self.rdram[offset:offset+4])[0]
        elif region == "PIF_ROM":
            return struct.unpack('>I', self.pif_rom[offset:offset+4])[0]

    def write_word(self, address, value):
        """Write a 32-bit word to memory"""
        region, offset = self.map_address(address)
        self.writes += 4
        
        if region == "RDRAM":
            self.rdram[offset:offset+4] = struct.pack('>I', value)
        elif region == "PIF_ROM":
            raise MemoryError("Cannot write to PIF ROM")
            
    def get_stats(self):
        """Return memory usage statistics"""
        return {
            'reads': self.reads,
            'writes': self.writes,
            'rdram_usage': np.count_nonzero(self.rdram) / self.RDRAM_SIZE * 100
        }

class Graphics:
    def __init__(self, canvas):
        self.canvas = canvas
        self.width = 640
        self.height = 480
        # Use numpy for framebuffer for better performance
        self.framebuffer = np.zeros((self.height, self.width), dtype=np.uint16)
        self.image = Image.new("RGB", (self.width, self.height))
        self.pixels = self.image.load()

    def clear_screen(self, color=0):
        self.framebuffer.fill(color)

    def draw_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.framebuffer[y, x] = color

    def draw_rectangle(self, x, y, width, height, color):
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self.width, x + width)
        y2 = min(self.height, y + height)
        
        if x1 < x2 and y1 < y2:
            self.framebuffer[y1:y2, x1:x2] = color

    def render(self):
        # Convert framebuffer to RGB using numpy operations
        r = ((self.framebuffer >> 10) & 0x1F) * 8
        g = ((self.framebuffer >> 5) & 0x1F) * 8
        b = (self.framebuffer & 0x1F) * 8
        
        # Stack RGB components
        rgb_array = np.stack((r, g, b), axis=-1).astype(np.uint8)
        
        # Convert to PIL Image
        self.image = Image.fromarray(rgb_array, mode='RGB')
        self.photo = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

class Kernel:
    def __init__(self, memory, graphics):
        self.memory = memory
        self.graphics = graphics
        self.pc = 0
        self.registers = np.zeros(32, dtype=np.uint32)
        self.running = True
        self.cycles = 0

    def load_program(self, program):
        for i, byte in enumerate(program):
            self.memory.write_byte(i, byte)
        self.pc = 0

    def fetch_instruction(self):
        instruction = self.memory.read_word(self.pc)
        self.pc += 4
        self.cycles += 1
        return instruction

    def decode_instruction(self, instruction):
        opcode = instruction >> 26

        if opcode == 0:  # R-type
            rs = (instruction >> 21) & 0x1F
            rt = (instruction >> 16) & 0x1F
            rd = (instruction >> 11) & 0x1F
            funct = instruction & 0x3F
            
            if funct == 0x20:  # ADD
                def func():
                    self.registers[rd] = (self.registers[rs] + self.registers[rt]) & 0xFFFFFFFF
                return func
            elif funct == 0x22:  # SUB
                def func():
                    self.registers[rd] = (self.registers[rs] - self.registers[rt]) & 0xFFFFFFFF
                return func

        elif opcode == 0x08:  # ADDI
            rs = (instruction >> 21) & 0x1F
            rt = (instruction >> 16) & 0x1F
            imm = instruction & 0xFFFF
            if imm & 0x8000:  # Sign-extend
                imm -= 0x10000
            def func():
                self.registers[rt] = (self.registers[rs] + imm) & 0xFFFFFFFF
            return func

        elif opcode == 0x0F:  # LUI
            rt = (instruction >> 16) & 0x1F
            imm = instruction & 0xFFFF
            def func():
                self.registers[rt] = imm << 16
            return func

        elif opcode == 0x2D:  # Draw rectangle
            def func():
                x = self.registers[1]
                y = self.registers[2]
                w = self.registers[3]
                h = self.registers[4]
                color = self.registers[5]
                self.graphics.draw_rectangle(x, y, w, h, color)
            return func

        elif opcode == 0x2E:  # Render framebuffer
            def func():
                self.graphics.render()
                time.sleep(0.016)  # ~60 FPS
            return func

        elif opcode == 0x3F:  # Halt
            def func():
                self.running = False
            return func

        else:
            def func():
                raise ValueError(f"Unknown opcode: {opcode}")
            return func

    def run(self):
        try:
            while self.running:
                instruction = self.fetch_instruction()
                self.decode_instruction(instruction)()
                
        except Exception as e:
            messagebox.showerror("Emulation Error", str(e))
            self.running = False

class GameWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("N64 Emulator")
        self.geometry("640x480")

        self.canvas = tk.Canvas(self, bg="black", width=640, height=480)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.memory = Memory()
        self.graphics = Graphics(self.canvas)
        self.kernel = Kernel(self.memory, self.graphics)

        # Create menu
        self.create_menu()
        
        # Demo program that uses more memory
        self.demo_program = [
            # Load upper immediate and add immediate to set up larger addresses
            (0x0F << 26) | (1 << 16) | 0x0001,      # lui r1, 0x0001
            (0x08 << 26) | (1 << 21) | (1 << 16) | 0x0000,  # addi r1, r1, 0x0000
            
            # Set up rectangle parameters
            (0x08 << 26) | (2 << 21) | (2 << 16) | 100,     # addi r2, r0, 100
            (0x08 << 26) | (3 << 21) | (3 << 16) | 200,     # addi r3, r0, 200
            (0x08 << 26) | (4 << 21) | (4 << 16) | 150,     # addi r4, r0, 150
            (0x08 << 26) | (5 << 21) | (5 << 16) | 0x1F,    # addi r5, r0, 0x1F
            
            (0x2D << 26),                           # draw rectangle
            (0x2E << 26),                           # render
            (0x3F << 26),                           # halt
        ]

        self.kernel.load_program(self.demo_program)
        self.after(100, self.start_emulation)

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load ROM", command=self.load_rom)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        debug_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Debug", menu=debug_menu)
        debug_menu.add_command(label="Memory Stats", command=self.show_memory_stats)

    def load_rom(self):
        filename = filedialog.askopenfilename(
            filetypes=[("N64 ROMs", "*.z64 *.n64 *.v64")]
        )
        if filename:
            try:
                with open(filename, 'rb') as f:
                    rom_data = f.read()
                self.kernel.load_program(rom_data)
                self.start_emulation()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ROM: {str(e)}")

    def start_emulation(self):
        self.kernel.run()

    def show_memory_stats(self):
        stats = self.memory.get_stats()
        messagebox.showinfo("Memory Statistics",
                          f"Memory Reads: {stats['reads']}\n"
                          f"Memory Writes: {stats['writes']}\n"
                          f"RDRAM Usage: {stats['rdram_usage']:.2f}%")

if __name__ == "__main__":
    app = GameWindow()
    app.mainloop()
