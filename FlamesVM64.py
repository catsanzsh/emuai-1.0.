import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random
import time
from PIL import Image, ImageTk
import json
import struct

class Memory:
    def __init__(self, size):
        self.size = size
        self.memory = bytearray(size)

    def read_byte(self, address):
        if 0 <= address < self.size:
            return self.memory[address]
        else:
            raise MemoryError(f"Invalid memory read at address: 0x{address:08x}")

    def write_byte(self, address, value):
        if 0 <= address < self.size:
            self.memory[address] = value & 0xFF
        else:
            raise MemoryError(f"Invalid memory write at address: 0x{address:08x}")

    def read_word(self, address):
        if 0 <= address + 3 < self.size:
            return struct.unpack('>I', self.memory[address:address+4])[0]
        else:
            raise MemoryError(f"Invalid memory read at address: 0x{address:08x}")

    def write_word(self, address, value):
        if 0 <= address + 3 < self.size:
            self.memory[address:address+4] = struct.pack('>I', value)
        else:
            raise MemoryError(f"Invalid memory write at address: 0x{address:08x}")

class Graphics:
    def __init__(self, canvas):
        self.canvas = canvas
        self.width = 640
        self.height = 480
        self.framebuffer = [0] * (self.width * self.height)

    def clear_screen(self, color=0):
        self.framebuffer = [color] * (self.width * self.height)

    def draw_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            index = y * self.width + x
            self.framebuffer[index] = color

    def render(self):
        # This is a very simplified rendering process
        img = Image.new("RGB", (self.width, self.height))
        pixels = img.load()

        for y in range(self.height):
            for x in range(self.width):
                index = y * self.width + x
                color = self.framebuffer[index]
                # Convert simple color index to RGB (very basic mapping)
                r = (color >> 5) & 0x07
                g = (color >> 2) & 0x07
                b = color & 0x03
                pixels[x, y] = (r * 32, g * 32, b * 64)  # Simple color conversion

        self.photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

class Kernel:
    def __init__(self, memory, graphics):
        self.memory = memory
        self.graphics = graphics
        self.pc = 0  # Program Counter
        self.registers = [0] * 32
        self.running = True

    def load_program(self, program):
        # Very basic program loading (just copy into memory)
        for i, byte in enumerate(program):
            self.memory.write_byte(i, byte)
        self.pc = 0

    def fetch_instruction(self):
        instruction = self.memory.read_word(self.pc)
        self.pc += 4
        return instruction

    def execute_instruction(self, instruction):
        # Extremely simplified instruction decoding and execution
        opcode = instruction >> 26  # Extract opcode (top 6 bits)

        if opcode == 0:  # Example: R-type instruction (simplified)
            rs = (instruction >> 21) & 0x1F
            rt = (instruction >> 16) & 0x1F
            rd = (instruction >> 11) & 0x1F
            # funct = instruction & 0x3F

            # Example: Add two registers
            self.registers[rd] = self.registers[rs] + self.registers[rt]

        elif opcode == 1:
            rs = (instruction >> 21) & 0x1F
            imm = instruction & 0xFFFF
            self.registers[rs]+=imm

        elif opcode == 2: # Example J-type
            target = instruction & 0x3FFFFFF
            self.pc = (self.pc & 0xF0000000) | (target << 2) # Very simple jump

        elif opcode == 3:  # Example: Draw pixel
            x = self.registers[1]
            y = self.registers[2]
            color = self.registers[3]
            self.graphics.draw_pixel(x, y, color)

        elif opcode == 4:
            self.graphics.render()
            time.sleep(0.05)

        elif opcode == 63:  # Example: Halt
            self.running = False

        else:
            raise ValueError(f"Unknown opcode: {opcode}")

    def run(self):
      while self.running:
        instruction = self.fetch_instruction()
        self.execute_instruction(instruction)

class GameWindow(tk.Toplevel):
    def __init__(self, parent, rom_path):
        super().__init__(parent)
        self.title("Game Window")
        self.geometry("640x480")

        # Create game canvas
        self.canvas = tk.Canvas(self, bg="black", width=640, height=480)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Initialize memory and graphics
        self.memory = Memory(1024 * 1024 * 24) # Emulate 24MB of RAM
        self.graphics = Graphics(self.canvas)

        # Load ROM data
        self.rom_path = rom_path
        self.load_rom()

        # Initialize kernel
        self.kernel = Kernel(self.memory, self.graphics)
        
        # Set up simple demo program
        demo_program = [
            0x01 << 26 | 1 << 21 | 10 << 16, # addi r1, r0, 10 (r1 = 10)
            0x01 << 26 | 2 << 21 | 5 << 16,  # addi r2, r0, 5 (r2 = 5)
            0x03 << 26,                      # draw pixel (x=r1, y=r2, color=7)
            0x01 << 26 | 2 << 21 | 1 << 16,
            0x01 << 26 | 3 << 21 | 4 << 16,
            0x00 << 26 | 1 << 21 | 2 << 16 | 3 << 11, # add r3, r1, r2 (r3 = r1 + r2)
            0x03 << 26,
            0x04 << 26,                     # render
            0x3F << 26,                      # halt
        ]
        self.kernel.load_program(demo_program)
        self.kernel.run()

        # Bind keys
        self.bind_controls()

    def load_rom(self):
        try:
            with open(self.rom_path, 'rb') as f:
                self.rom_data = f.read()
            self.canvas.create_text(320, 240, text="ROM Loaded Successfully", fill="white")
        except Exception as e:
            self.canvas.create_text(320, 240, text=f"Error loading ROM: {str(e)}", fill="red")

    def bind_controls(self):
        self.bind('<KeyPress>', self.handle_keypress)
        self.bind('<KeyRelease>', self.handle_keyrelease)

    def handle_keypress(self, event):
        # Handle key press events based on controller configuration
        pass

    def handle_keyrelease(self, event):
        # Handle key release events
        pass

class CheatManager:
    def __init__(self):
        self.cheats = []

    def add_cheat(self, code, description):
        self.cheats.append({
            'code': code,
            'description': description,
            'enabled': False
        })

    def toggle_cheat(self, index):
        if 0 <= index < len(self.cheats):
            self.cheats[index]['enabled'] = not self.cheats[index]['enabled']

    def apply_cheats(self, memory):
        for cheat in self.cheats:
            if cheat['enabled']:
                # Parse and apply GameShark code
                self.apply_gameshark_code(cheat['code'], memory)

    def apply_gameshark_code(self, code, memory):
        # GameShark code interpretation logic
        code = code.replace(" ", "")
        if len(code) == 12:  # Standard GameShark code length
            address = int(code[2:6], 16)
            value = int(code[6:], 16)
            # Modify memory at address
            memory[address] = value

class WiiVirtualConsole:
    def __init__(self, root):
        self.root = root
        self.root.title("Wii Virtual Console")
        self.root.geometry("800x600")
        self.root.configure(bg="#1a1a1a")

        # Initialize managers
        self.cheat_manager = CheatManager()
        self.controller_config = self.load_controller_config()

        self.setup_styles()
        self.setup_menu()

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Setup tabs
        self.setup_main_tab()
        self.setup_controller_tab()
        self.setup_cheats_tab()

        self.emulation_running = False
        self.loaded_rom = None

    def setup_styles(self):
        style = ttk.Style()
        # Configure modern looking styles
        style.configure("TNotebook", background="#1a1a1a", borderwidth=0)
        style.configure("TNotebook.Tab", padding=[10, 5], font=('Arial', 10))
        style.configure("TFrame", background="#1a1a1a")
        style.configure("TButton", padding=5, font=('Arial', 10))
        style.configure("TLabel", background="#1a1a1a", foreground="white", font=('Arial', 10))

    def setup_main_tab(self):
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="Games")

        # Game selection area
        game_frame = ttk.Frame(main_frame)
        game_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title and info
        ttk.Label(game_frame, text="Virtual Console",
                 font=('Arial', 24, 'bold')).pack(pady=10)

        # Game list
        self.game_listbox = tk.Listbox(game_frame, bg="#2a2a2a", fg="white",
                                     font=('Arial', 12), height=10)
        self.game_listbox.pack(fill=tk.BOTH, expand=True, pady=10)

        # Buttons
        button_frame = ttk.Frame(game_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Load ROM",
                  command=self.load_rom).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Start Game",
                  command=self.start_game).pack(side=tk.LEFT, padx=5)

    def setup_controller_tab(self):
        controller_frame = ttk.Frame(self.notebook)
        self.notebook.add(controller_frame, text="Controller")

        # Controller configuration
        ttk.Label(controller_frame, text="Controller Configuration",
                 font=('Arial', 16, 'bold')).pack(pady=10)

        # Button mapping frame
        mapping_frame = ttk.Frame(controller_frame)
        mapping_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # Create mapping entries for each button
        self.button_vars = {}
        buttons = ['A', 'B', 'Start', 'C-Up', 'C-Down', 'C-Left', 'C-Right',
                  'D-Up', 'D-Down', 'D-Left', 'D-Right', 'L', 'R', 'Z']

        for i, button in enumerate(buttons):
            row = i // 2
            col = i % 2

            frame = ttk.Frame(mapping_frame)
            frame.grid(row=row, column=col, padx=10, pady=5, sticky='w')

            ttk.Label(frame, text=f"{button}:").pack(side=tk.LEFT)

            var = tk.StringVar(value=self.controller_config.get(button, 'None'))
            self.button_vars[button] = var

            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind('<KeyPress>', lambda e, b=button: self.capture_key(e, b))

    def setup_cheats_tab(self):
        cheats_frame = ttk.Frame(self.notebook)
        self.notebook.add(cheats_frame, text="Cheats")

        # Cheats list
        ttk.Label(cheats_frame, text="GameShark Codes",
                 font=('Arial', 16, 'bold')).pack(pady=10)

        # Cheat list frame
        self.cheat_frame = ttk.Frame(cheats_frame)
        self.cheat_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        # Add cheat button
        ttk.Button(cheats_frame, text="Add Code",
                  command=self.add_cheat_dialog).pack(pady=10)

    def load_controller_config(self):
        try:
            with open('controller_config.json', 'r') as f:
                return json.load(f)
        except:
            return {
                'A': 'x', 'B': 'z', 'Start': 'Return',
                'C-Up': 'i', 'C-Down': 'k', 'C-Left': 'j', 'C-Right': 'l',
                'D-Up': 'Up', 'D-Down': 'Down', 'D-Left': 'Left', 'D-Right': 'Right',
                'L': 'a', 'R': 's', 'Z': 'space'
            }

    def save_controller_config(self):
        config = {k: v.get() for k, v in self.button_vars.items()}
        with open('controller_config.json', 'w') as f:
            json.dump(config, f)

    def capture_key(self, event, button):
        self.button_vars[button].set(event.keysym)
        return "break"

    def load_rom(self):
        filetypes = [("N64 ROMs", "*.z64 *.n64 *.v64")]
        filename = filedialog.askopenfilename(filetypes=filetypes)

        if filename:
            self.loaded_rom = filename
            rom_name = os.path.basename(filename)
            self.game_listbox.insert(tk.END, rom_name)

    def start_game(self):
        if not self.loaded_rom:
            messagebox.showerror("Error", "Please load a ROM first")
            return

        # Create game window
        game_window = GameWindow(self.root, self.loaded_rom)

    def add_cheat_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add GameShark Code")
        dialog.geometry("300x200")

        ttk.Label(dialog, text="Code:").pack(pady=5)
        code_entry = ttk.Entry(dialog)
        code_entry.pack(pady=5)

        ttk.Label(dialog, text="Description:").pack(pady=5)
        desc_entry = ttk.Entry(dialog)
        desc_entry.pack(pady=5)

        def add_code():
            code = code_entry.get()
            desc = desc_entry.get()
            if code and desc:
                self.cheat_manager.add_cheat(code, desc)
                self.update_cheat_list()
                dialog.destroy()

        ttk.Button(dialog, text="Add", command=add_code).pack(pady=10)

    def update_cheat_list(self):
        # Clear existing cheats
        for widget in self.cheat_frame.winfo_children():
            widget.destroy()

        # Add each cheat to the list
        for i, cheat in enumerate(self.cheat_manager.cheats):
            frame = ttk.Frame(self.cheat_frame)
            frame.pack(fill=tk.X, pady=2)

            var = tk.BooleanVar(value=cheat['enabled'])
            cb = ttk.Checkbutton(frame, variable=var,
                               command=lambda idx=i: self.cheat_manager.toggle_cheat(idx))
            cb.pack(side=tk.LEFT)

            ttk.Label(frame, text=f"{cheat['code']} - {cheat['description']}").pack(side=tk.LEFT)

if __name__ == "__main__":
    root = tk.Tk()
    app = WiiVirtualConsole(root)
    root.mainloop()
