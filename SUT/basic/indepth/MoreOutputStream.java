/*
 * MoreOutputStream.java
 *
 * Written 23-May-96 by Chuck McManis
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

import java.io.*;
import java.awt.*;


public class MoreOutputStream extends OutputStream {
    Frame myFrame;
    TextArea ta;
    StringBuffer sb = new StringBuffer();

    public MoreOutputStream() {
        Dimension d = new Dimension(640, 480);
        myFrame = new Frame("Console Output");

        Font f = new Font("Courier", Font.PLAIN, 14);
        myFrame.setFont(f);
        ta = new TextArea(24, 80);
        myFrame.add("Center", ta);

        myFrame.resize(d);
        myFrame.show(true);
        ta.show(true);
        myFrame.repaint();

    }

    public void write(int b) throws IOException {


        sb.append((char) b);
        if (b == '\n') {
            ta.appendText(sb.toString());
            sb.setLength(0);
        }
    }

    public void write(byte b[], int off, int len) throws IOException {


        for (int i = 0; i < len; i++) {
            write((char) b[i+off]);
        }
    }

    public void write(byte b[]) throws IOException {
        for (int i = 0; i < b.length; i++) {
            write((char) b[i]);
        }
    }
}
