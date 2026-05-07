/*
 * BASIC.java -  BASIC Interpreter in Java.
 *
 * Copyright (c) 1996 Chuck McManis, All Rights Reserved.
 *
 * Permission to use, copy, modify, and distribute this software
 * and its documentation for NON-COMMERCIAL purposes and without
 * fee is hereby granted provided that this copyright notice
 * appears in all copies.
 *
 * CHUCK MCMANIS MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE
 * SUITABILITY OF THE SOFTWARE, EITHER EXPRESS OR IMPLIED, INCLUDING
 * BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT. CHUCK MCMANIS
 * SHALL NOT BE LIABLE FOR ANY DAMAGES SUFFERED BY LICENSEE AS A RESULT
 * OF USING, MODIFYING OR DISTRIBUTING THIS SOFTWARE OR ITS DERIVATIVES.
 */
package basic;

//import java.io.*;
//
//
//public class BASIC {
//    public static void main(String[] args) {
//        char[] data = new char[256];
//        LexicalTokenizer lt = new LexicalTokenizer(data);
//        Console con;
//
//        ConsoleWindow cw = new ConsoleWindow("Java BASIC 1.0");
//          // Ensure the window is visible
//        CommandInterpreter ci = new CommandInterpreter(cw.DataInputStream(),
//                                    cw.PrintStream());
//        try {
//            ci.start();
//        } catch (Exception e) {
//            System.out.println("Caught an Exception :");
//            e.printStackTrace();
//            try {
//                System.out.println("Press enter to continue.");
//                int c = System.in.read();
//            } catch (IOException ignored) { }
//        }
//    }
//}
import java.io.*;

public class BASIC {
    public static void main(String[] args) {
        // Use System.in for input and System.out for output
        InputStream inputStream = System.in;
        PrintStream outputStream = System.out;

        CommandInterpreter ci = new CommandInterpreter(new DataInputStream(inputStream),
                outputStream);

        try {
            ci.start();
            outputStream.flush();  // Start the BASIC interpreter with standard I/O
        } catch (Exception e) {
            System.out.println("Caught an Exception :");
            e.printStackTrace();
            try {
                System.out.println("Press enter to continue.");
                int c = System.in.read();  // Wait for the user to press enter
            } catch (IOException ignored) { }
        }
    }
}
