import sys
import re
import os

#supported instruction set
R_type = {"add" : ["0"*7, "000"], "sub" : ["01"+"0"*5, "000"], "slt" : ["0"*7, "010"], "srl" : ["0"*7, "101"], "or" : ["0"*7, "110"], "and" : ["0"*7, "111"]}
I_type = ["lw", "addi", "jalr"]
S_type = ["sw"]
B_type = ["beq", "bne", "blt"]
J_type = ["jal"]

#register naming in RV32-I
REGISTERS = {
    "zero": "00000", "ra": "00001", "sp": "00010", "gp": "00011", "tp": "00100",
    "t0": "00101", "t1": "00110", "t2": "00111", "s0": "01000", "s1": "01001",
    "a0": "01010", "a1": "01011", "a2": "01100", "a3": "01101", "a4": "01110", "a5": "01111","a6": "10000",
    "a7": :10001","s2": "10010", "s3": "10011", "s4": "10100", "s5": "10101", "s6": "10110", "s7": "10111",
    "s8": "11000", "s9": "11001", "s10": "11010", "s11": "11011", "t3": "11100", "t4": "11101",
    "t5": "11110", "t6": "11111"
}

#2's complement and sign extension 
def to_bin(n):
    n=int(n)
    bin = ""
    if n>=0:
        while (n > 0):
            r = n % 2
            n = n // 2
            bin += str(r)
        if (len(bin) < 12):
            bin = "0"*(12 - len(bin)) + bin[::-1]
    else:
        n=n*(-1)
        while (n > 0):
            r = 1-(n % 2)
            n = n // 2
            bin += str(r)
            bin=list(bin)
            for d in range (len(bin)):
                if bin[d]=='0':
                    bin[d]='1'
                    break
                else:
                    bin[d]='0'
            bin=''.join(bin)
        if (len(bin) < 12):
            bin = "1"*(12 - len(bin)) + bin[::-1]
    return bin

def B_type_assembler(instr, rs1, rs2, imm):

    if (rs1 not in REGISTERS):
        raise ValueError(f"{rs1} not a valid register")
    if (rs2 not in REGISTERS):
        raise ValueError(f"{rs2} not a valid register")

    imm = int(imm)
    if (imm < -2048 or imm > 2047):
        raise ValueError("Immediate value out of range")
    
    B_OPCODE = '1100011'
    f = {'beq': '000', 'bne': '001', 'blt': '100'}.get(instr, '')
    if not f:
        raise ValueError(f"Invalid B-type instruction: {instr}")
    
    assert (imm % 4) == 0, "Immediate must be a multiple of 4"
    return ''.join([
        f'{(imm >> 12) & 0x1:01b}',    # imm[12]
        f'{(imm >> 5) & 0x3f:06b}',    # imm[10:5]
        REGISTERS[rs2],             
        REGISTERS[rs1],
        f,
        f'{(imm >> 1) & 0xf:04b}',     # imm[4:1]
        f'{(imm >> 11) & 0x1:01b}',    # imm[11]
        B_OPCODE
    ])

def I_type_assembler(instr, rd, rs1, imm):

    if (rs1 not in REGISTERS):
        raise ValueError(f"{rs1} not a valid register")
    if (rd not in REGISTERS):
        raise ValueError(f"{rd} not a valid register")

    imm = int(imm)
    if (imm < -2048 or imm > 2047):
        raise ValueError("Immediate value out of range")

    if instr == "lw":
        funct3 = "010"  
        opcode = "0000011" 
    elif instr == "addi":
        funct3 = "000"  
        opcode = "0010011" 
    elif instr == "jalr":
        funct3 = "000"  
        opcode = "1100111" 
    else:
        raise ValueError(f"Unsupported I-type instruction: {instr}")
    imm_bin = f"{imm & 0xFFF:012b}" 
    rs1_bin = REGISTERS[rs1]
    rd_bin = REGISTERS[rd]
    return imm_bin + rs1_bin + funct3 + rd_bin + opcode

#combining everything together
def assemble(labels, instructions, output_file):
    with open(output_file, 'w') as out:
        for pc, tokens in instructions:
            if not tokens:
                continue
            instr_type = tokens[0]

            if instr_type in B_type:
                assert len(tokens) == 4, f"Wrong usage in line {pc//4 + 1}. Usage: func rs1,rs2,imm"
                rs1, rs2, imm = tokens[1], tokens[2], tokens[3]

                if (imm.isalnum() and not imm.isdigit() and imm not in labels):
                    raise ValueError(f"{imm} not in labels")
                if imm in labels:
                    imm = labels[imm] - pc  # Convert label to offset

                binary = B_type_assembler(instr_type, rs1, rs2, imm)
                out.write(binary + '\n')


            elif instr_type in J_type:

                assert len(tokens) == 3, f"Wrong Usage in line {pc//4 + 1}. Usage: func rd,imm"

                if (tokens[1] not in REGISTERS):
                    raise ValueError(f"{tokens[1]} not a valid register")
                rd = REGISTERS[tokens[1]]
                imm = tokens[2]
                if (imm.isalnum() and not imm.isdigit() and imm not in labels):
                    raise ValueError(f"{imm} not in labels")
                if imm in labels:
                    imm = labels[imm] - pc
                assert (int(imm) % 4) == 0, "Immediate must be a multiple of 4"

                imm = int(imm)
                if (imm < -2048 or imm > 2047):
                    raise ValueError("Immediate value out of range")

                imm = imm // 2
                imm = format(imm & 0x7FFFF, '019b')
                if imm[0] == '1':
                    imm = '1' + imm
                else:
                    imm = '0' + imm
                binary=imm[0]+imm[10:20]+imm[9]+imm[1:9]+rd+'1101111'
                out.write(binary + '\n')


            elif instr_type in I_type:

                if instr_type == "lw":
                    assert len(tokens) == 4, f"Wrong Usage in line {pc//4 + 1}. Usage: func rd,imm(rs1)"
                    rd, imm, rs1 = tokens[1], tokens[2], tokens[3]
                else:
                    assert len(tokens) == 4, f"Wrong Usage in line {pc//4 + 1}. Usage: func rd,rs,imm"
                    rd, rs1, imm = tokens[1], tokens[2], tokens[3]
                
                if (imm.isalnum() and not imm.isdigit() and imm not in labels):
                    raise ValueError(f"{imm} not in labels")
                if imm in labels:
                    imm = labels[imm] - pc
                imm=int(imm)
                if (imm < -2048 or imm > 2047):
                    raise ValueError("Immediate value out of range")

                binary = I_type_assembler(instr_type, rd, rs1, imm)
                out.write(binary + '\n') 


            elif instr_type in S_type:

                assert len(tokens) == 4, f"Wrong Usage in line {pc//4 + 1}. Usage: func rs2,imm(rs1)"

                if (tokens[1] not in REGISTERS):
                    raise ValueError(f"{tokens[1]} not a valid register")
                if (tokens[3] not in REGISTERS):
                    raise ValueError(f"{tokens[3]} not a valid register")

                rs2 = REGISTERS[tokens[1]]
                imm = tokens[2]

                if (imm.isalnum() and not imm.isdigit() and imm not in labels):
                    raise ValueError(f"{imm} not in labels")
                if imm in labels:
                    imm = labels[imm] - pc
                imm = int(imm)

                if (imm < -2048 or imm > 2047):
                    raise ValueError("Immediate value out of range")

                imm = to_bin(imm)
                rs1 = REGISTERS[tokens[3]]
                binary = imm[0:7]+rs2+rs1+'010'+imm[7::]+'0100011'
                out.write(binary + '\n')


            elif instr_type in R_type:

                assert len(tokens) == 4, f"Wrong Usage in line {pc//4 + 1}. Usage: func rd,rs1,rs2"
                if (tokens[1] not in REGISTERS):
                    raise ValueError(f"{tokens[1]} not a valid register")
                if (tokens[2] not in REGISTERS):
                    raise ValueError(f"{tokens[2]} not a valid register")
                if (tokens[3] not in REGISTERS):
                    raise ValueError(f"{tokens[3]} not a valid register")

                f7 = R_type[instr_type][0]
                f3 = R_type[instr_type][1]
                rd = REGISTERS[tokens[1]]
                rs1 = REGISTERS[tokens[2]]
                rs2 = REGISTERS[tokens[3]]
                binary  = f7 + rs2 + rs1 + f3 + rd + "0110011"
                out.write(binary + '\n')
            else:
                binary = "Unsupported instruction"
                break

#taking input from the file            
def assembler(input_file, output_file):

    '''storing labels and instructions, labels is a dictionary while instructions 
    in and array of 2-tuple, where first entry is pc and second entry if instruction
    in the form of array of tokens'''

    labels = {}
    instructions = []
    with open(input_file, 'r') as f:
        pc = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(':', 1)
            if len(parts) == 2:
                labels[parts[0].strip()] = pc
                instruction_part = parts[1].strip()
            else:
                instruction_part = parts[0].strip()
            if instruction_part:
                tokens = re.split(r'[ ,()]+', instruction_part) 
                tokens = [t for t in tokens if t]   
                instructions.append((pc, tokens))
                pc += 4

    assemble(labels, instructions, output_file)

def main():

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    assembler(input_file,output_file)

main()
