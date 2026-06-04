
package basic;

import java.util.*;

/** a simple Queue class, which accepts the same methods as Stack objects,
  bit is FIFO rather than LIFO.
  */
public class Queue extends BaseObject
{	private LList head;
	private LList tail;

	/** the number of elements currently enqueued */
	public int elementCount=0;
	/** returns true if the Queue is empty */
	public boolean empty() { return (head==null); }
	/** make it be empty */
	public synchronized void flush() { head = tail = null; elementCount=0; }

	/** peek a look at the next element */
	public Object peek() 
	{ if(head!=null) 
		{ return(head.Contents()); 
		}
		else throw new EmptyStackException();
	}
	/** add a new element */
	public synchronized void push(Object x) 
		{ LList item = new LList(x,null);
		  if(tail!=null) 
			{ tail.Set_Next(item);
			}
			else
			{ head = item;
			}
			tail = item;
			elementCount++;
		} 
	/** remove the oldest element */
  public synchronized Object pop()
  {	if(head!=null) 
  	 { LList val = head;
  	 	 head=head.Next(); 
  	 	 if(head==null) {tail=null;}
  	 	 elementCount--;
	  	 return(((LList) val).Contents());
	   }
  else {throw new EmptyStackException(); }
  }
}