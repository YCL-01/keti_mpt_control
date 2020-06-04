//------------------------------------//
// AUTHOR   : Youngchan Lim
//------------------------------------//

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <fcntl.h>
#include <ctype.h>
#include <termios.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <time.h>

//------------------------------------------------------------------------//
// socket
#define port 5030

// Memory R/W
#define MAP_SIZE 4096UL 			// Memory Paging Size 4KB
#define MAP_MASK (MAP_SIZE - 1) 	// Memory Address Mask
#define MAXLINE 511 				// buf max
#define COMMAND_ERROR "Unknown command!!"

#define ARTIX_1_SFR 0x40400000
#define ARTIX_2_SFR 0x40C00000
#define ARTIX_3_SFR 0x41400000
#define ARTIX_4_SFR 0x41C00000

#define ARTIX_1_MEM 0x40000000
#define ARTIX_2_MEM 0x40800000
#define ARTIX_3_MEM 0x41000000
#define ARTIX_4_MEM 0x41800000

#define RX_CTRL		0x2C8
#define RX_REF_B	0xAC9
#define RX_REF_A	0xAC8

unsigned long read_SFR(int fd, off_t target);
void write_SFR(int fd, off_t target, unsigned long value);
void Reset_modem(int fd, off_t target);
void rx_cal_bd(int sock, struct sockaddr_in cliaddr, int addrlen);					// FFT calibration for whole FPGA board
void tx_cal_bd(int sock, struct sockaddr_in cliaddr, int addrlen, off_t target);
void retro_continuous();

int main()
{
	// --------------------- < socket > --------------------- //

	struct sockaddr_in servaddr, cliaddr;           // Zynq, PC

    int sock;										// socket
    int addrlen = sizeof(struct sockaddr);

    if((sock = socket(PF_INET, SOCK_DGRAM, 0)) < 0) 
    {
        perror("socket fail");
        exit(0);
    } // UDP connect error

 	// server structure
    memset(&cliaddr, 0, addrlen); 
    memset(&servaddr, 0, addrlen); 
    servaddr.sin_family = AF_INET;
    servaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    servaddr.sin_port = htons(port); //access
    if(bind(sock,(struct sockaddr *)&servaddr, addrlen) < 0) 
    {
        perror("bind fail");
        exit(0);
    }

    // --------------------- < memory access > -------------------- //

    char recv_buf[MAXLINE+1];                            			// Command From PC
    char send_buf[MAXLINE+1];										// result to PC

	int fd = open("/dev/mem",O_RDWR|O_SYNC);						// Memory open with RD,WR & SYNC(realtime)
	void *map_base;
	void *virt_addr;												// For mmap function

	char *cmd;														// command
	char *target_data;												// designated target
	char *value_data;												// designated value
	
	off_t target;													// memory address	
	unsigned long value;											// input data to SFR
	unsigned long result;											// output data from SFR

	int i = 0;


	// -------------------- < Execution part > -------------------- // 

	while(1)
	{
		// reset buffer and reset file descriptor
		cmd = NULL;
		memset(recv_buf,0,sizeof(recv_buf));
		memset(send_buf,0,sizeof(send_buf));
		close(fd);
		fd = 0;
		fd = open("/dev/mem",O_RDWR|O_SYNC);

		// receive command and memory address to access
		recvfrom(sock, recv_buf, MAXLINE, 0, (struct sockaddr *)&cliaddr, &addrlen);

		// Tokenize command
		cmd = strtok(recv_buf, " ");					// command
		target_data = strtok(NULL, " ");				// target
		value_data = strtok(NULL, " ");					// input value
		target = strtoul(target_data, 0, 0);			//string to unsigned long
		value = strtoul(value_data, 0, 0);
		printf(" - command: %c\n - target: %s\n - value: %s \n", cmd[0], target_data, value_data);
		
		//switch case for function select by command
		switch(cmd[0])
		{
			case 'r': // read SFR
				sprintf(send_buf,"%03lx",read_SFR(fd, target));
				sendto(sock,send_buf,strlen(send_buf),0,(struct sockaddr *)&cliaddr, sizeof(cliaddr));
				break;

			case 'w': // write input value to designated SFR area
				write_SFR(fd, target, value);
				break;

			case 'b': // reset bp_comp(ARTIX)
				write_SFR(fd, ARTIX_1_SFR + 0x410, value);
				write_SFR(fd, ARTIX_2_SFR + 0x410, value);
				write_SFR(fd, ARTIX_3_SFR + 0x410, value);
				write_SFR(fd, ARTIX_4_SFR + 0x410, value);
				break;

			case 'x': // rx disable
				write_SFR(fd, ARTIX_1_SFR, 0x0);

				write_SFR(fd, ARTIX_1_SFR + 0x414, 0x0);
				write_SFR(fd, ARTIX_2_SFR + 0x414, 0x0);
				write_SFR(fd, ARTIX_3_SFR + 0x414, 0x0);
				write_SFR(fd, ARTIX_4_SFR + 0x414, 0x0);
				break;

			case 'l': // rx_cal by FFT(BOARD)
				close(fd);
				rx_cal_bd(sock, cliaddr, addrlen);
				break;

			case 'c': // Continuous Retro reflective
				close(fd);
				retro_continuous();
				break;
	
			default:
				printf("wrong command");
				break;
		}	
	}
}

unsigned long read_SFR(int fd, off_t target)
{
	void *map_base;
	void *virt_addr;
	unsigned long output;
	map_base = mmap(0,MAP_SIZE,PROT_WRITE | PROT_READ, MAP_SHARED,fd,target&~MAP_MASK);
	virt_addr = map_base+(target & MAP_MASK);
	output = *((unsigned long *)virt_addr);
	munmap(map_base,MAP_SIZE);
	return output;
}

void write_SFR(int fd, off_t target, unsigned long value)
{
	void *map_base;
	void *virt_addr;
	map_base = mmap(0,MAP_SIZE,PROT_WRITE | PROT_READ, MAP_SHARED,fd,target&~MAP_MASK);
	virt_addr = map_base+(target & MAP_MASK);
	*(unsigned long*)virt_addr = value;
	munmap(map_base,MAP_SIZE);
}

void rx_cal_bd(int sock, struct sockaddr_in cliaddr, int addrlen)
{
	// --------- < Variables > --------- //
	int fd = open("/dev/mem",O_RDWR|O_SYNC);	// Memory open with RD,WR & SYNC(realtime)
	void *map_base;
	void *virt_addr;
	
	off_t target_ARTIX[4] = {ARTIX_1_SFR, ARTIX_2_SFR, ARTIX_3_SFR, ARTIX_4_SFR};
	off_t mem_target_ARTIX[4] = {ARTIX_1_MEM, ARTIX_2_MEM, ARTIX_3_MEM, ARTIX_4_MEM};
	off_t target_temp;
	off_t mem_target_temp;
	
	char *trash = {0};
	char mem_data[3000] = {0};								// ADC memory
	char recv_buf[MAXLINE] = {0};							// Cal data
	char buf_rx_e_value[MAXLINE] = {0};						// Estimated data
	char *cal_data = {0};									// FFT calibrated data	

	unsigned long cal_val[32] = {0};						// rx_calibration value from PC
	unsigned long rstatus = 0;							 	// rstatus for calculation confirm
	unsigned long output;									// output for read_SFR()

	int i = 0;
	int j = 0;
	int k = 0;

	for(i=0; i<4; i++){
		printf("slept %d sec\n", i);
		sleep(1);
	}

	// ------------ Rx disable ------------ //
	write_SFR(fd, target_ARTIX[0], 0x0);							// global rx disable
	printf("rx disabled\n");
	sleep(1);

	// ------------ rstatus to 0 ------------ //
	for(i = 0; i < 4; i++)
	{
		target_temp = target_ARTIX[i] + 0x414;
		write_SFR(fd, target_temp, 0x0);
	}
	printf("rstatus resettled\n");
	
	// ------------ ADC clock Ref BD ------------ //
	target_temp = target_ARTIX[0] + 0x410;
	write_SFR(fd, target_temp, RX_REF_B);

	// ------------ Rx enable ------------ //
	write_SFR(fd, target_ARTIX[0], 0x10);							// global rx enable
	printf("rx enabled\n");
	sleep(1);

	// ------------ Memory dump ------------ //
	while(1) 
	{					
	// check rstatus for rx cal

		target_temp = target_ARTIX[0] + 0x414;
		rstatus = read_SFR(fd, target_temp);
		printf("rstatus : %lx\n",rstatus);

		if(rstatus == 0 )
		{
			usleep(1000);
			close(fd);
			fd = 0;
			fd = open("/dev/mem",O_RDWR|O_SYNC);
			continue;
		}
		else 
		{
			for(k = 0; k < 4; k++)																			// 4 ARTIX
			{
				mem_target_temp = mem_target_ARTIX[k];
				for(j = 0; j < 4; j++)
				{																							// 4 channel
					target_temp = mem_target_temp;
					printf("\ntarget: %lx\n", mem_target_temp);
					for(i=0;i<500;i++) 																		// I val
					{
						sprintf(mem_data,"%s %03lx",mem_data, read_SFR(fd, target_temp));
						target_temp = target_temp + 0x04;
					}
					sendto(sock,mem_data,strlen(mem_data),0,(struct sockaddr *)&cliaddr, sizeof(cliaddr));
					memset(mem_data,0,sizeof(mem_data));

					mem_target_temp = mem_target_temp + 0x40000;
					printf("\ntarget: %lx\n", mem_target_temp);
					target_temp = mem_target_temp;
					for(i=0;i<500;i++) 																		// Q val
					{
						sprintf(mem_data,"%s %03lx",mem_data, read_SFR(fd, target_temp));

						target_temp = target_temp + 0x04;
					}
					sendto(sock,mem_data,strlen(mem_data),0,(struct sockaddr *)&cliaddr, sizeof(cliaddr));	// dumped memory send
					memset(mem_data,0,sizeof(mem_data));
					mem_target_temp = mem_target_temp + 0xc0000;
				}
			}
			break;
		}
	}

	i = 0;
	j = 0;
 	k = 0;

 	// ------------ Rx disable ------------ //
	write_SFR(fd, target_ARTIX[0], 0x0);

	for(i=0; i<12; i++){
		sleep(1);
		printf("slept for %d sec\n", i+1);
	}

	// ------------ Cal val receive and save ------------ //
	recvfrom(sock, recv_buf, MAXLINE, 0, (struct sockaddr *)&cliaddr, &addrlen);
	printf("recv: %s\n", recv_buf);
	trash = strtok(recv_buf, " ");
	for(i=0; i<32; i++)
	{
		cal_data = strtok(NULL, " ");
		cal_val[i] = strtoul(cal_data ,0 ,0);
	}

	//------------ Write Cal val ------------//
	for(j = 0; j < 4; j++)
	{
		target_temp = target_ARTIX[j] + 0x1400;
		for(i=0; i < 8; i++){
			write_SFR(fd, target_temp, cal_val[(j*8 + i)]);
			target_temp = target_temp + 0x08;
		}
	}
	memset(cal_val,0,sizeof(cal_val));
	i = 0;
	j = 0;
 	k = 0;
	
	// ------------ rstatus to 0 ------------ //
	for(i = 0; i < 4; i++)
	{
		target_temp = target_ARTIX[i] + 0x414;
		write_SFR(fd, target_temp, 0x0);
	}

	// ------------ Rx_cal_comp_bp_done ------------ //

	target_temp = target_ARTIX[0] + 0x410;

	write_SFR(fd, target_temp, RX_REF_A);

	for(i = 1; i < 4; i++)
	{
		target_temp = target_ARTIX[i] + 0x410;
		write_SFR(fd, target_temp, RX_CTRL);
	}

	// ------------ Rx enable ------------ //
	write_SFR(fd, target_ARTIX[0], 0x10);
	sleep(1);

	while(1) 
	{				
		// check rstatus for rx cal
		target_temp = target_ARTIX[0] + 0x414;
		rstatus = read_SFR(fd, target_temp);
		
		if(rstatus == 0) 
		{
			usleep(10000);
			close(fd);
			fd = 0;
			fd = open("/dev/mem",O_RDWR|O_SYNC);
			continue;
		}
		else 
		{
			for(k = 0; k < 4; k++)																			// 4 ARTIX
			{
				mem_target_temp = mem_target_ARTIX[k];
				for(j = 0; j < 4; j++)
				{																							// 4 channel
					target_temp = mem_target_temp;
					printf("\ntarget: %lx\n", mem_target_temp);
					for(i=0;i<500;i++) 																		// I val
					{
						sprintf(mem_data,"%s %03lx",mem_data, read_SFR(fd, target_temp));
						target_temp = target_temp + 0x04;
					}
					sendto(sock,mem_data,strlen(mem_data),0,(struct sockaddr *)&cliaddr, sizeof(cliaddr));
					memset(mem_data,0,sizeof(mem_data));

					mem_target_temp = mem_target_temp + 0x40000;
					printf("\ntarget: %lx\n", mem_target_temp);
					target_temp = mem_target_temp; 
					for(i=0;i<500;i++) // Q val
					{
						sprintf(mem_data,"%s %03lx",mem_data, read_SFR(fd, target_temp));
						target_temp = target_temp + 0x04;
					}
					// dumped memory send
					sendto(sock,mem_data,strlen(mem_data),0,(struct sockaddr  *)&cliaddr, sizeof(cliaddr));
					memset(mem_data,0,sizeof(mem_data));
					mem_target_temp = mem_target_temp + 0xc0000;
				}
			}
			break;
		}
	}
}

void tx_cal_bd(int sock, struct sockaddr_in cliaddr, int addrlen, off_t target)
{
	// --------- < Variables > --------- //
	int fd = open("/dev/mem",O_RDWR|O_SYNC);	// Memory open with RD,WR & SYNC(realtime)
	void *map_base;
	void *virt_addr;
	
	off_t target_ARTIX[4] = {ARTIX_1_SFR, ARTIX_2_SFR, ARTIX_3_SFR, ARTIX_4_SFR};
	off_t target_temp;
	
	char *trash = {0};
	char recv_buf[MAXLINE] = {0};							// Cal data
	char *cal_data = {0};									// FFT calibrated data
	unsigned long cal_val[16] = {0};						// rx_calibration value from PC

	int i = 0;
	int j = 0;
	int k = 0;
	// --------- < Tx calibration value recv > --------- //
	recvfrom(sock, recv_buf, MAXLINE, 0, (struct sockaddr *)&cliaddr, &addrlen);
	printf(" %s\n",recv_buf);
	
	trash = strtok(recv_buf, " ");
	for(i=0; i<16; i++){
		cal_data = strtok(NULL, " ");
		cal_val[i] = strtoul(cal_data ,0 ,0);
	}
	cal_val[0] = 0;

	// --------- < Write Cal val > --------- //
	for(j = 0; j < 4; j++)
	{
		target_temp = target_ARTIX[j] + 0xC0;
		for(i=0; i<4; i++){
			write_SFR(fd, target_temp, cal_val[k]);
			k ++;
			target_temp = target_temp + 0x08;
		}
	}
	memset(cal_val,0,sizeof(cal_val));
}

void retro_continuous()
{
	// ---- < Variables > ---- //
	int fd = open("/dev/mem",O_RDWR|O_SYNC);	// Memory open with RD,WR & SYNC(realtime)
	void *map_base;
	void *virt_addr;
	off_t target_ARTIX[4] = {ARTIX_1_SFR, ARTIX_2_SFR, ARTIX_3_SFR, ARTIX_4_SFR};
	off_t target_temp = 0;
	off_t rstatus = 0;
	
	int i = 0;

	// ------------ Rx disable ------------ //
	write_SFR(fd, target_ARTIX[0], 0x0);

	for(i=0;i<4;i++)
	{
		target_temp = target_ARTIX[i] + 0x414;
		write_SFR(fd, target_temp, 0x0); // rstatus to 0
	}


	// ------------ Rx enable ------------ //
	write_SFR(fd, target_ARTIX[0], 0x10);

	while(1) {
		target_temp = target_ARTIX[0] + 0x414;
		rstatus = read_SFR(fd, target_temp);

		if(rstatus == 0)
		{
			printf(" No signal detected!\n");
			close(fd);
			fd = 0;
			fd = open("/dev/mem",O_RDWR|O_SYNC);
			usleep(10000);
			continue;
		}
		else
		{
			// ------------ Rx disable ------------ //
			write_SFR(fd, target_ARTIX[0], 0x0);

			for(i=0;i<4;i++)
			{
				target_temp = target_ARTIX[i] + 0x414;
				write_SFR(fd, target_temp, 0x0); // rstatus to 0
			}

			// ------------ Tx enable ------------ //
			write_SFR(fd, target_ARTIX[0], 0x20);
			usleep(8500); 						// sleep for 8ms
			
			close(fd);
			fd = 0;
			fd = open("/dev/mem",O_RDWR|O_SYNC);

			// ------------ Tx disable ------------ //
			write_SFR(fd, target_ARTIX[0], 0x0);

			// ------------ Rx enable ------------ //
			write_SFR(fd, target_ARTIX[0], 0x10);
			usleep(1500); 						// sleep for 1.5ms
		}
	}
}
